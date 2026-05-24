#!/usr/bin/env python3
"""Ingest a source video — from YouTube URL or local file path —
into the skill's memory directory.

Usage:
    01_ingest.py <url-or-path> [--slug SLUG]

If --slug is omitted, derives from YouTube title or filename.

Output:
    ~/.claude/skills/sermon-cuts/memory/messages/<slug>/source.mp4
    ~/.claude/skills/sermon-cuts/memory/messages/<slug>/meta.json
"""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"


def slugify(text: str) -> str:
    """ASCII snake_case slug."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text[:60] or "untitled"


def ingest_youtube(url: str, slug: str | None) -> tuple[Path, dict]:
    # Probe metadata first to derive slug
    probe = subprocess.run(
        ["yt-dlp", "-J", "--no-warnings", url],
        capture_output=True, text=True, check=True,
    )
    meta = json.loads(probe.stdout)
    title = meta.get("title", "video")
    duration = meta.get("duration", 0)
    slug = slug or slugify(title)
    msg_dir = MESSAGES / slug
    msg_dir.mkdir(parents=True, exist_ok=True)
    out = msg_dir / "source.mp4"
    if out.exists():
        print(f"[skip] {out} already exists", file=sys.stderr)
    else:
        # Download best video+audio merged to mp4, prefer 1080p
        subprocess.run([
            "yt-dlp",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
            "--merge-output-format", "mp4",
            "-o", str(out),
            url,
        ], check=True)
    meta_out = {
        "source_type": "youtube",
        "url": url,
        "title": title,
        "duration_s": duration,
        "slug": slug,
    }
    (msg_dir / "meta.json").write_text(json.dumps(meta_out, indent=2, ensure_ascii=False))
    return out, meta_out


def ingest_local(path: Path, slug: str | None) -> tuple[Path, dict]:
    slug = slug or slugify(path.stem)
    msg_dir = MESSAGES / slug
    msg_dir.mkdir(parents=True, exist_ok=True)
    out = msg_dir / "source.mp4"
    if out.exists():
        print(f"[skip] {out} already exists", file=sys.stderr)
    else:
        # Symlink to save disk (sources can be huge). Copy as fallback.
        try:
            out.symlink_to(path.resolve())
        except OSError:
            shutil.copy2(path, out)
    # Probe duration via ffprobe
    dur = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(out),
    ], capture_output=True, text=True)
    duration = float(dur.stdout.strip() or 0)
    meta_out = {
        "source_type": "local",
        "path": str(path),
        "title": path.stem,
        "duration_s": duration,
        "slug": slug,
    }
    (msg_dir / "meta.json").write_text(json.dumps(meta_out, indent=2, ensure_ascii=False))
    return out, meta_out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--slug", default=None)
    args = ap.parse_args()

    s = args.source
    is_url = s.startswith(("http://", "https://"))
    if is_url:
        out, meta = ingest_youtube(s, args.slug)
    else:
        out, meta = ingest_local(Path(s), args.slug)

    print(json.dumps({
        "ok": True,
        "slug": meta["slug"],
        "source_path": str(out),
        "duration_s": meta["duration_s"],
        "message_dir": str(out.parent),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
