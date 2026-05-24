#!/usr/bin/env python3
"""Transcribe source video with word-level timestamps.

Two providers:
  --provider=youtube  (default): yt-dlp downloads auto-captions, parse VTT
                       inline word timestamps. Free, instant, sometimes makes
                       small word-level mistakes you'll want to correct manually.
  --provider=groq:     Extract audio, send to Groq Whisper-large-v3. Slower
                       (~30s per 10min audio) but much higher accuracy. Needs
                       GROQ_API_KEY in env.

For the youtube provider, the source must have been ingested with a stored
`meta.json` containing the URL.

Usage:
    02_transcribe.py <slug> [--provider=youtube|groq] [--language=pt] [--force]

Reads:  memory/messages/<slug>/source.mp4
        memory/messages/<slug>/meta.json
Writes: memory/messages/<slug>/transcript.json

Output schema (same shape for both providers):
{
  "words": [{"text": "Eu", "start": 1.95, "end": 2.12, "type": "word"},
            {"text": " ", "start": 2.12, "end": 2.13, "type": "spacing"}, ...],
  "language": "pt",
  "_provider": "youtube-vtt" | "groq-whisper-large-v3"
}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _common import SCHEMA_VERSION, fail, resolve_ffmpeg

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())
FFMPEG = resolve_ffmpeg(CFG.get("ffmpeg_bin"))


def load_env() -> None:
    if os.environ.get("GROQ_API_KEY"):
        return
    for env_path in (Path.home() / ".env", Path.cwd() / ".env", Path.cwd() / "edit/.env"):
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ─── YouTube VTT provider ──────────────────────────────────────────────────

TS_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")
CUE_HEADER_RE = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})")
INLINE_TS_RE = re.compile(r"<(\d{2}:\d{2}:\d{2}\.\d{3})>")
TAG_RE = re.compile(r"<[^>]+>")


def _ts_to_seconds(s: str) -> float:
    m = TS_RE.match(s)
    if not m:
        return 0.0
    h, mn, sc, ms = m.groups()
    return int(h) * 3600 + int(mn) * 60 + int(sc) + int(ms) / 1000.0


def _parse_vtt_cue(cue_start: float, cue_end: float, text: str) -> list[dict]:
    text = text.replace("\n", " ").strip()
    if not text:
        return []
    chunks: list[tuple[float, str]] = []
    last_pos = 0
    last_ts = cue_start
    for m in INLINE_TS_RE.finditer(text):
        chunks.append((last_ts, text[last_pos : m.start()]))
        last_ts = _ts_to_seconds(m.group(1))
        last_pos = m.end()
    chunks.append((last_ts, text[last_pos:]))
    out: list[dict] = []
    for i, (start, raw) in enumerate(chunks):
        clean = TAG_RE.sub("", raw).strip()
        if not clean:
            continue
        end = chunks[i + 1][0] if i + 1 < len(chunks) else cue_end
        words = clean.split()
        if len(words) == 1:
            out.append({"start": start, "end": end, "text": words[0]})
        else:
            dur = max(0.01, end - start) / len(words)
            for j, w in enumerate(words):
                out.append(
                    {
                        "start": start + j * dur,
                        "end": start + (j + 1) * dur,
                        "text": w,
                    }
                )
    return out


def _parse_vtt_file(vtt_path: Path) -> list[dict]:
    text = vtt_path.read_text()
    blocks = re.split(r"\n\n+", text)
    all_words: list[dict] = []
    for block in blocks:
        raw_lines = block.splitlines()
        timing_idx = None
        for i, line in enumerate(raw_lines):
            if CUE_HEADER_RE.match(line):
                timing_idx = i
                break
        if timing_idx is None:
            continue
        m = CUE_HEADER_RE.match(raw_lines[timing_idx])
        if not m:
            continue
        start = _ts_to_seconds(m.group(1))
        end = _ts_to_seconds(m.group(2))
        body_lines = [ln for ln in raw_lines[timing_idx + 1 :] if INLINE_TS_RE.search(ln)]
        if not body_lines:
            continue
        body = "\n".join(body_lines)
        all_words.extend(_parse_vtt_cue(start, end, body))
    all_words.sort(key=lambda w: w["start"])
    seen: set[tuple[str, int]] = set()
    deduped: list[dict] = []
    for w in all_words:
        key = (w["text"].lower(), int(round(w["start"] * 20)))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(w)
    return deduped


def transcribe_youtube(url: str, language: str, work_dir: Path) -> dict:
    out_template = str(work_dir / "subs.%(ext)s")
    subprocess.run(
        [
            "yt-dlp",
            "--write-auto-subs",
            "--sub-langs",
            f"{language}.*,{language}",
            "--sub-format",
            "vtt",
            "--skip-download",
            "--no-warnings",
            "-o",
            out_template,
            url,
        ],
        check=True,
        stderr=subprocess.PIPE,
    )
    vtt_candidates = sorted(work_dir.glob("*.vtt"))
    if not vtt_candidates:
        raise RuntimeError(f"no VTT auto-captions returned by yt-dlp for {url}")
    vtt = vtt_candidates[0]
    print(f"  parsed VTT: {vtt.name}", file=sys.stderr)
    raw_words = _parse_vtt_file(vtt)
    return {
        "words": _to_scribe_shape(raw_words),
        "language": language,
        "_provider": "youtube-vtt",
    }


# ─── Groq provider ─────────────────────────────────────────────────────────


def _extract_audio(src: Path, out: Path) -> None:
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            "-c:a",
            "pcm_s16le",
            str(out),
        ],
        check=True,
        stderr=subprocess.DEVNULL,
    )


def transcribe_groq(src: Path, language: str) -> dict:
    load_env()
    if not os.environ.get("GROQ_API_KEY"):
        fail(
            "GROQ_API_KEY não configurada",
            hint="adicione `GROQ_API_KEY=gsk_...` no ~/.env ou exporte no shell. "
            "Alternativa: use --provider=youtube (legendas auto, grátis).",
            url="https://console.groq.com/keys",
        )
    from groq import Groq

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    try:
        print("  extracting mono16k audio...", file=sys.stderr)
        _extract_audio(src, wav)
        size_mb = wav.stat().st_size / 1e6
        print(f"  sending to Groq Whisper-large-v3 ({size_mb:.1f} MB)...", file=sys.stderr)
        client = Groq()
        with open(wav, "rb") as f:
            resp = client.audio.transcriptions.create(
                file=(wav.name, f.read()),
                model="whisper-large-v3",
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
    finally:
        wav.unlink(missing_ok=True)
    raw = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
    raw_words = [
        {
            "start": float(w.get("start") or 0),
            "end": float(w.get("end") or w.get("start") or 0),
            "text": (w.get("word") or w.get("text") or "").strip(),
        }
        for w in raw.get("words", [])
        if (w.get("word") or w.get("text"))
    ]
    return {
        "words": _to_scribe_shape(raw_words),
        "language": raw.get("language", language),
        "_provider": "groq-whisper-large-v3",
    }


# ─── shared post-processing ────────────────────────────────────────────────


def _to_scribe_shape(raw_words: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev_end = None
    for w in raw_words:
        s = float(w["start"])
        e = float(w["end"])
        text = (w["text"] or "").strip()
        if not text:
            continue
        if prev_end is not None and s > prev_end + 0.001:
            out.append({"text": " ", "start": prev_end, "end": s, "type": "spacing"})
        out.append({"text": text, "start": s, "end": e, "type": "word"})
        prev_end = e
    return out


# ─── main ──────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--provider", choices=["youtube", "groq"], default="youtube")
    ap.add_argument("--language", default="pt")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    src = msg_dir / "source.mp4"
    out = msg_dir / "transcript.json"
    if not src.exists():
        fail(
            f"source não encontrado: {src}",
            hint=f"rode primeiro: ./scripts/pipeline.sh <url-ou-mp4>  (ou: 01_ingest.py <src> --slug {args.slug})",
        )
    if out.exists() and not args.force:
        print(json.dumps({"ok": True, "skipped": True, "path": str(out)}, indent=2))
        return

    meta = json.loads((msg_dir / "meta.json").read_text())

    if args.provider == "youtube":
        if meta.get("source_type") != "youtube" or not meta.get("url"):
            fail(
                "--provider=youtube precisa de um source vindo do YouTube",
                hint="esse slug foi ingerido de arquivo local. Use --provider=groq "
                "(requer GROQ_API_KEY) ou --provider=local (offline com faster-whisper).",
            )
        with tempfile.TemporaryDirectory() as td:
            payload = transcribe_youtube(meta["url"], args.language, Path(td))
    else:
        payload = transcribe_groq(src, args.language)

    payload["_schema_version"] = SCHEMA_VERSION
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    n_words = sum(1 for w in payload["words"] if w.get("type") == "word")
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(out),
                "n_words": n_words,
                "language": payload["language"],
                "provider": payload["_provider"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
