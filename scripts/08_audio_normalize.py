#!/usr/bin/env python3
"""Normalize a cut's audio to -14 LUFS with true-peak limiting.

Uses ffmpeg's ``loudnorm`` filter (EBU R128 + true-peak control) in proper
two-pass mode: measure first, then apply the corrective gain bounded by a
true-peak ceiling so the output never clips.

Why not pyloudnorm? The previous implementation used pyloudnorm to apply a
flat gain, then fell back to dividing-by-peak if the result exceeded 1.0 —
which silently undid part of the loudness target (post-scale signal was
quieter than -14 LUFS) and reported a misleading ``post_peak`` from before
the scale-down. ffmpeg's ``loudnorm`` filter does proper EBU R128 with a
true-peak limiter built in, which is the broadcast / streaming-platform
standard.

Usage:
    08_audio_normalize.py <slug> <cut_index>
                          [--target-lufs -14.0] [--true-peak-db -1.5]
                          [--in-place]

Reads:
    memory/messages/<slug>/cuts_proposed.json
    memory/messages/<slug>/renders/NN-slug.mp4
Writes:
    memory/messages/<slug>/renders/NN-slug.normalized.mp4
    (or overwrites NN-slug.mp4 if --in-place)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _common import fail, resolve_ffmpeg

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())
FFMPEG = resolve_ffmpeg(CFG.get("ffmpeg_bin"))
DEFAULT_LUFS = CFG["audio"]["target_lufs"]
DEFAULT_TRUE_PEAK = -1.5  # dBTP — safe headroom for Insta/TikTok/Reels


def _loudnorm_pass1_measure(src: Path, target_lufs: float, tp_db: float) -> dict:
    """Pass 1: measure integrated loudness + true peak. Returns ffmpeg stats."""
    proc = subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(src),
            "-af",
            f"loudnorm=I={target_lufs}:TP={tp_db}:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    # loudnorm prints its JSON stats to stderr after a leading log block.
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', proc.stderr, re.DOTALL)
    if not m:
        raise RuntimeError(
            f"loudnorm pass 1 failed to emit stats. ffmpeg stderr tail:\n{proc.stderr[-800:]}"
        )
    return json.loads(m.group(0))


def _loudnorm_pass2_apply(
    src: Path, dst: Path, target_lufs: float, tp_db: float, stats: dict
) -> None:
    """Pass 2: apply gain using measured stats, with true-peak limit baked in."""
    af = (
        f"loudnorm=I={target_lufs}:TP={tp_db}:LRA=11:"
        f"measured_I={stats['input_i']}:"
        f"measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:"
        f"measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:"
        f"linear=true:print_format=summary"
    )
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(src),
            "-map",
            "0:v",
            "-map",
            "0:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-af",
            af,
            "-movflags",
            "+faststart",
            str(dst),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    ap.add_argument("--target-lufs", type=float, default=DEFAULT_LUFS)
    ap.add_argument("--true-peak-db", type=float, default=DEFAULT_TRUE_PEAK)
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    cuts = json.loads((msg_dir / "cuts_proposed.json").read_text())
    cut = cuts[args.cut_index - 1]
    n = cut.get("n", args.cut_index)
    slug = cut["slug"]
    src = msg_dir / "renders" / f"{n:02d}-{slug}.mp4"
    if not src.exists():
        fail(
            f"render não encontrado: {src}",
            hint=f"rode primeiro: ./scripts/07_render_track.py {args.slug} {args.cut_index}",
        )
    final = src.with_name(f"{n:02d}-{slug}.normalized.mp4")

    stats = _loudnorm_pass1_measure(src, args.target_lufs, args.true_peak_db)
    _loudnorm_pass2_apply(src, final, args.target_lufs, args.true_peak_db, stats)

    if args.in_place:
        final.replace(src)
        final = src

    print(
        json.dumps(
            {
                "ok": True,
                "path": str(final),
                "size_mb": round(final.stat().st_size / (1024 * 1024), 1),
                "target_lufs": args.target_lufs,
                "true_peak_db": args.true_peak_db,
                "measured_input_i": float(stats["input_i"]),
                "measured_input_tp": float(stats["input_tp"]),
                "measured_input_lra": float(stats["input_lra"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
