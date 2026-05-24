#!/usr/bin/env python3
"""Voice Activity Detection: find natural pause boundaries in the source audio.

Usage:
    03_vad_segments.py <slug> [--min-silence 0.5]

Reads:  memory/messages/<slug>/source.mp4
Writes: memory/messages/<slug>/vad.json

Schema:
{
  "speech": [{"start": 0.34, "end": 12.18}, ...],   # speech segments
  "silences": [{"start": 12.18, "end": 13.05, "duration": 0.87}, ...],
  "candidate_cut_points": [12.18, 28.71, ...]       # mid-silence times,
                                                     # good places to split
}

Cut boundaries should land in silences ≥ min_silence (default 0.5s) so the
audio doesn't snap mid-breath.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"


def extract_wav_16k(src: Path, out: Path) -> None:
    subprocess.run([
        FFMPEG, "-y", "-i", str(src),
        "-ac", "1", "-ar", "16000", "-vn",
        "-c:a", "pcm_s16le", str(out),
    ], check=True, stderr=subprocess.DEVNULL)


def run_vad(wav: Path) -> list[dict]:
    """Run silero-vad on a 16kHz mono WAV. Returns list of {start,end} in seconds.

    We read via soundfile (avoids torchaudio→torchcodec dependency surprise),
    convert to torch float32, then pass to get_speech_timestamps.
    """
    import torch
    import soundfile as sf
    from silero_vad import load_silero_vad, get_speech_timestamps
    model = load_silero_vad()
    data, sr = sf.read(str(wav), dtype="float32")
    assert sr == 16000, f"expected 16k, got {sr}"
    if data.ndim > 1:
        data = data.mean(axis=1)
    audio = torch.from_numpy(data)
    ts = get_speech_timestamps(audio, model, sampling_rate=16000)
    return [{"start": t["start"] / 16000.0, "end": t["end"] / 16000.0} for t in ts]


def derive_silences(speech: list[dict], total_dur: float, min_silence: float) -> tuple[list[dict], list[float]]:
    """From speech segments, compute silences between them, then pick midpoint
    of each silence ≥ min_silence as a candidate cut point."""
    silences: list[dict] = []
    candidates: list[float] = []
    # Pre-roll silence (before first speech)
    if speech and speech[0]["start"] > min_silence:
        sil = {"start": 0.0, "end": speech[0]["start"], "duration": speech[0]["start"]}
        silences.append(sil)
        candidates.append(sil["end"] - 0.1)  # snap right before speech starts
    # Between segments
    for a, b in zip(speech, speech[1:]):
        dur = b["start"] - a["end"]
        if dur >= min_silence:
            sil = {"start": a["end"], "end": b["start"], "duration": dur}
            silences.append(sil)
            # Cut point: 0.1s after speech ends (avoids cutting trailing breath)
            candidates.append(a["end"] + 0.15)
    # Post-roll silence
    if speech and total_dur - speech[-1]["end"] > min_silence:
        sil = {"start": speech[-1]["end"], "end": total_dur,
               "duration": total_dur - speech[-1]["end"]}
        silences.append(sil)
        candidates.append(speech[-1]["end"] + 0.15)
    return silences, candidates


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--min-silence", type=float, default=0.5,
                    help="silences shorter than this are not cut candidates")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    src = msg_dir / "source.mp4"
    out = msg_dir / "vad.json"
    if not src.exists():
        sys.exit(f"source not found: {src}")
    if out.exists() and not args.force:
        print(json.dumps({"ok": True, "skipped": True, "path": str(out)}))
        return

    # Get total duration from meta
    meta = json.loads((msg_dir / "meta.json").read_text())
    total_dur = float(meta.get("duration_s", 0))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    try:
        print(f"[1/2] extracting mono16k WAV for VAD...", file=sys.stderr)
        extract_wav_16k(src, wav)
        print(f"[2/2] running silero-vad on {total_dur:.1f}s audio...", file=sys.stderr)
        speech = run_vad(wav)
    finally:
        wav.unlink(missing_ok=True)

    silences, candidates = derive_silences(speech, total_dur, args.min_silence)
    payload = {
        "speech": speech,
        "silences": silences,
        "candidate_cut_points": candidates,
        "min_silence_s": args.min_silence,
        "total_duration_s": total_dur,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps({
        "ok": True,
        "path": str(out),
        "n_speech_segments": len(speech),
        "n_silences": len(silences),
        "n_candidate_cuts": len(candidates),
    }, indent=2))


if __name__ == "__main__":
    main()
