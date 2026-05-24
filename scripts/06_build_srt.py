#!/usr/bin/env python3
"""Build a brand-styled SRT for a cut segment.

Chunking rules (from CLAUDE.md / video_brand_style.md):
- 3-4 words per cue, max ~20 chars
- Function-word-aware breaks (don't end a cue on "para", "que", "com"…)
- Sentence case (capitalize first cue if Whisper starts lowercase)
- ≥0.5s pause forces a flush
- Strip trailing soft punctuation (,;:) from cue text

Usage:
    06_build_srt.py <slug> <cut_index>

Reads:
    memory/messages/<slug>/transcript.json
    memory/messages/<slug>/cuts_proposed.json
Writes:
    memory/messages/<slug>/srts/NN-slug.srt
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())
SUB_CFG = CFG["subtitle"]
MIN_WORDS = SUB_CFG["min_words"]
MAX_WORDS = SUB_CFG["max_words"]
MAX_CHARS = SUB_CFG["max_chars"]
PUNCT_BREAK = set(".!?")
SOFT_BREAK = set(",;:")
FUNC = set(
    w for line in (SKILL_ROOT / "config/function_words_pt.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
    for w in line.split()
)


def srt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _norm(t: str) -> str:
    return t.strip(",.;:!?").lower()


def _is_function(text: str) -> bool:
    return _norm(text) in FUNC


def _chunk_chars(chunk: list[dict]) -> int:
    return sum(len((w.get("text") or "").strip()) for w in chunk) + max(0, len(chunk) - 1)


def build_srt(words: list[dict], seg_start: float, seg_end: float) -> list[tuple[float, float, str]]:
    in_range = [
        w for w in words
        if w.get("type") == "word"
        and w.get("start") is not None
        and w.get("end") is not None
        and w["end"] > seg_start
        and w["start"] < seg_end
    ]
    chunks: list[list[dict]] = []
    cur: list[dict] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            chunks.append(cur)
            cur = []

    prev_end: float | None = None
    for w in in_range:
        text = (w.get("text") or "").strip()
        if prev_end is not None and (w["start"] - prev_end) >= 0.5 and len(cur) >= MIN_WORDS:
            flush()
        if cur and _chunk_chars(cur) + 1 + len(text) > MAX_CHARS and len(cur) >= MIN_WORDS:
            flush()
        cur.append(w)
        last_char = text[-1] if text else ""
        if last_char in PUNCT_BREAK:
            flush()
        elif last_char in SOFT_BREAK and len(cur) >= MIN_WORDS:
            flush()
        elif len(cur) >= MAX_WORDS:
            flush()
        prev_end = w["end"]
    flush()

    # Function-word shift (keep last chunk intact — don't shift its trailing function word)
    for i in range(len(chunks) - 2):
        while chunks[i] and _is_function((chunks[i][-1].get("text") or "")):
            if len(chunks[i]) <= 2:
                break
            shifted_text = (chunks[i][-1].get("text") or "").strip()
            if _chunk_chars(chunks[i + 1]) + 1 + len(shifted_text) > MAX_CHARS:
                break
            shifted = chunks[i].pop()
            chunks[i + 1].insert(0, shifted)
    chunks = [c for c in chunks if c]

    entries: list[tuple[float, float, str]] = []
    for chunk in chunks:
        ws = max(seg_start, float(chunk[0]["start"]))
        we = min(seg_end, float(chunk[-1]["end"]))
        out_start = max(0.0, ws - seg_start)
        out_end = max(out_start + 0.4, we - seg_start)
        text = " ".join((w.get("text") or "").strip() for w in chunk).strip()
        text = text.rstrip(",;:")
        entries.append((out_start, out_end, text))

    # Capitalize first cue
    if entries:
        a, b, t = entries[0]
        if t and t[0].islower():
            entries[0] = (a, b, t[0].upper() + t[1:])
    return entries


def write_srt(entries: list[tuple[float, float, str]], path: Path) -> None:
    lines: list[str] = []
    for i, (a, b, t) in enumerate(entries, 1):
        lines.append(str(i))
        lines.append(f"{srt_ts(a)} --> {srt_ts(b)}")
        lines.append(t)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    args = ap.parse_args()
    msg_dir = MESSAGES / args.slug
    transcript = json.loads((msg_dir / "transcript.json").read_text())
    cuts = json.loads((msg_dir / "cuts_proposed.json").read_text())
    cut = cuts[args.cut_index - 1]
    n = cut.get("n", args.cut_index)
    slug = cut["slug"]
    seg_start = float(cut["start"])
    seg_end = float(cut["end"])

    srts_dir = msg_dir / "srts"
    srts_dir.mkdir(exist_ok=True)
    out = srts_dir / f"{n:02d}-{slug}.srt"
    entries = build_srt(transcript["words"], seg_start, seg_end)
    write_srt(entries, out)
    print(json.dumps({
        "ok": True,
        "path": str(out),
        "n_cues": len(entries),
        "duration_s": round(seg_end - seg_start, 2),
        "last_cue_text": entries[-1][2] if entries else "",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
