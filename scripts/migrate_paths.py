#!/usr/bin/env python3
"""One-shot migration: move user-visible MP4s out of memory/messages/.

Before this commit, sources and renders both lived under
``~/.claude/skills/sermon-cuts/memory/messages/<slug>/`` — hidden from
the Finder because the `.claude/` parent starts with a dot. Now they
live in the visible top-level dirs ``<repo>/sources/<slug>/`` and
``<repo>/renders/<slug>/``.

This script walks every existing slug and migrates its files to the
new layout. Idempotent and conservative:

  • source.mp4 → sources/<slug>/source.mp4 (moves the file or symlink)
  • renders/*.mp4 → renders/<slug>/*.mp4 (moves the whole directory)
  • Everything else (transcript.json, vad.json, srts/, meta.json,
    cuts_proposed.json, …) stays put — that's pipeline state.

Pass --dry-run to preview without moving. Default mode prints what it
moved, errors out cleanly on first conflict (won't clobber).

Usage:
    migrate_paths.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import resolve_messages_dir, resolve_renders_dir, resolve_sources_dir, warn

MESSAGES = resolve_messages_dir()
SOURCES = resolve_sources_dir()
RENDERS = resolve_renders_dir()


def _move(src: Path, dst: Path, dry_run: bool) -> str:
    if dst.exists():
        return f"  ✗ destino já existe (pulando): {dst}"
    if dry_run:
        return f"  → would move: {src} → {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"  ✓ moved: {src.name} → {dst}"


def migrate(dry_run: bool) -> dict:
    if not MESSAGES.exists():
        warn("nada pra migrar: memory/messages/ não existe")
        return {"moved_sources": 0, "moved_render_dirs": 0, "slugs": []}

    moved_sources = 0
    moved_render_dirs = 0
    touched_slugs: list[str] = []

    for slug_dir in sorted(MESSAGES.iterdir()):
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name
        if slug.startswith("."):
            continue

        slug_touched = False

        old_source = slug_dir / "source.mp4"
        if old_source.exists() or old_source.is_symlink():
            new_source = SOURCES / slug / "source.mp4"
            line = _move(old_source, new_source, dry_run)
            print(line, file=sys.stderr)
            if line.startswith(("  ✓", "  →")):
                moved_sources += 1
                slug_touched = True

        old_renders = slug_dir / "renders"
        if old_renders.exists() and old_renders.is_dir():
            new_renders = RENDERS / slug
            line = _move(old_renders, new_renders, dry_run)
            print(line, file=sys.stderr)
            if line.startswith(("  ✓", "  →")):
                moved_render_dirs += 1
                slug_touched = True

        if slug_touched:
            touched_slugs.append(slug)

    return {
        "moved_sources": moved_sources,
        "moved_render_dirs": moved_render_dirs,
        "slugs": touched_slugs,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="preview without moving")
    args = ap.parse_args()

    print(f"[migrate_paths] MESSAGES = {MESSAGES}", file=sys.stderr)
    print(f"[migrate_paths] SOURCES  = {SOURCES}", file=sys.stderr)
    print(f"[migrate_paths] RENDERS  = {RENDERS}", file=sys.stderr)
    print(file=sys.stderr)

    result = migrate(args.dry_run)
    result["ok"] = True
    result["dry_run"] = args.dry_run
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.dry_run and result["slugs"]:
        print("\nRe-run without --dry-run to actually move.", file=sys.stderr)


if __name__ == "__main__":
    main()
