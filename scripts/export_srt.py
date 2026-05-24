#!/usr/bin/env python3
"""Export a cut's SRT with ASS markup stripped, ready for third-party uploads.

Our brand SRTs carry inline ASS overrides like ``{\\fs22\\b1}`` on the
first cue so libass can render the hook line bigger during burn-in. That
markup is correct for the in-pipeline render, but if you upload the raw
SRT to YouTube CC or Instagram auto-captions, those platforms display the
``{\\fs22\\b1}`` characters literally — ugly.

This script reads the canonical SRT and writes a sibling ``.clean.srt``
with all ``{...}`` overrides removed, preserving cue numbers and timing
exactly. Idempotent — re-running just overwrites the clean copy.

Usage:
    export_srt.py <slug> <cut_index> [--stdout]

Reads:  memory/messages/<slug>/srts/NN-slug.srt
Writes: memory/messages/<slug>/srts/NN-slug.clean.srt   (default)
        stdout                                          (with --stdout)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import fail, resolve_messages_dir

ASS_OVERRIDE_RE = re.compile(r"\{[^}]*\}")


def strip_ass_markup(srt_text: str) -> str:
    """Remove all ``{...}`` ASS override blocks from an SRT.

    Conservative: only strips well-formed brace pairs. Leaves naked ``{``
    or ``}`` characters alone (they're more likely intentional than a
    truncated override).
    """
    return ASS_OVERRIDE_RE.sub("", srt_text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="print to stdout instead of writing to .clean.srt",
    )
    args = ap.parse_args()

    msg_dir = resolve_messages_dir() / args.slug
    cuts = json.loads((msg_dir / "cuts_proposed.json").read_text())
    cut = cuts[args.cut_index - 1]
    n = cut.get("n", args.cut_index)
    slug = cut["slug"]
    src = msg_dir / "srts" / f"{n:02d}-{slug}.srt"
    if not src.exists():
        fail(
            f"SRT não encontrado: {src}",
            hint=f"rode primeiro: ./scripts/06_build_srt.py {args.slug} {args.cut_index}",
        )

    clean = strip_ass_markup(src.read_text())

    if args.stdout:
        sys.stdout.write(clean)
        return

    dst = src.with_suffix(".clean.srt")
    dst.write_text(clean)
    print(
        json.dumps(
            {
                "ok": True,
                "src": str(src),
                "dst": str(dst),
                "stripped_chars": len(src.read_text()) - len(clean),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
