#!/usr/bin/env python3
"""Normalize a cut's audio to -14 LUFS (Insta/TikTok/Reels standard).

Two-pass approach using pyloudnorm:
  1. Measure integrated loudness of source audio
  2. Apply gain to hit target_lufs (-14 default)
  3. Mux back into MP4 (audio replaced, video kept as-is)

Usage:
    08_audio_normalize.py <slug> <cut_index>
                          [--target-lufs -14.0] [--in-place]

Reads:
    memory/messages/<slug>/cuts_proposed.json
    memory/messages/<slug>/renders/NN-slug.mp4
Writes:
    memory/messages/<slug>/renders/NN-slug.normalized.mp4
    (or overwrites NN-slug.mp4 if --in-place)
"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
import yaml

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())
FFMPEG = CFG["ffmpeg_bin"]
DEFAULT_LUFS = CFG["audio"]["target_lufs"]


def extract_wav(src: Path, out: Path) -> tuple[int, int]:
    """Extract stereo audio at original sample rate as WAV. Returns (sr, channels)."""
    subprocess.run([
        FFMPEG, "-y", "-i", str(src),
        "-vn", "-c:a", "pcm_s16le",
        str(out),
    ], check=True, stderr=subprocess.DEVNULL)
    import soundfile as sf
    info = sf.info(str(out))
    return info.samplerate, info.channels


def measure_and_normalize(wav_in: Path, wav_out: Path, target_lufs: float) -> dict:
    import soundfile as sf
    import pyloudnorm as pyln
    import numpy as np
    data, rate = sf.read(str(wav_in))
    meter = pyln.Meter(rate)
    integrated = meter.integrated_loudness(data)
    if integrated == float("-inf"):
        # Silent track — leave as is
        sf.write(str(wav_out), data, rate)
        return {"integrated_lufs": None, "applied_gain_db": 0.0, "target_lufs": target_lufs}
    normalized = pyln.normalize.loudness(data, integrated, target_lufs)
    # Hard limit to avoid clipping
    peak = float(np.max(np.abs(normalized)))
    if peak > 1.0:
        normalized = normalized / peak * 0.999
    sf.write(str(wav_out), normalized, rate)
    return {
        "integrated_lufs": float(integrated),
        "applied_gain_db": float(target_lufs - integrated),
        "target_lufs": target_lufs,
        "post_peak": peak,
    }


def remux_audio(video_src: Path, audio_wav: Path, out: Path) -> None:
    """Replace audio in video_src with audio_wav, re-encode audio to AAC, copy video."""
    subprocess.run([
        FFMPEG, "-y",
        "-i", str(video_src), "-i", str(audio_wav),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out),
    ], check=True, stderr=subprocess.DEVNULL)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    ap.add_argument("--target-lufs", type=float, default=DEFAULT_LUFS)
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    cuts = json.loads((msg_dir / "cuts_proposed.json").read_text())
    cut = cuts[args.cut_index - 1]
    n = cut.get("n", args.cut_index)
    slug = cut["slug"]
    src = msg_dir / "renders" / f"{n:02d}-{slug}.mp4"
    if not src.exists():
        sys.exit(f"render not found: {src}")
    final = src.with_name(f"{n:02d}-{slug}.normalized.mp4")

    with tempfile.TemporaryDirectory() as td:
        wav_in = Path(td) / "in.wav"
        wav_out = Path(td) / "out.wav"
        sr, ch = extract_wav(src, wav_in)
        info = measure_and_normalize(wav_in, wav_out, args.target_lufs)
        remux_audio(src, wav_out, final)

    if args.in_place:
        final.replace(src)
        final = src

    print(json.dumps({
        "ok": True,
        "path": str(final),
        "size_mb": round(final.stat().st_size / (1024 * 1024), 1),
        **info,
    }, indent=2))


if __name__ == "__main__":
    main()
