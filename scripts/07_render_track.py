#!/usr/bin/env python3
"""Render a vertical 1080×1920 cut from a horizontal source using
MediaPipe face detection + smooth pan + brand subtitle burn.

Pipeline:
  Pass 1: Sample frames at SAMPLE_FPS, detect largest face with MediaPipe
          (BlazeFace short-range), record source-X center.
  Smooth: Moving average over SMOOTH_WINDOW_S seconds. Linear interpolate
          between samples for per-frame X.
  Pass 2: For each frame, scale to height 1920 preserving aspect,
          crop 1080 wide centered on smoothed X. Pipe raw BGR to ffmpeg.
  Mux:    Combine encoded video with source audio (segment-cut).
  Burn:   Apply subtitles filter with brand force_style.

Usage:
    07_render_track.py <slug> <cut_index> [--no-subs]

Reads:
    memory/messages/<slug>/source.mp4
    memory/messages/<slug>/cuts_proposed.json
    memory/messages/<slug>/srts/NN-slug.srt
Writes:
    memory/messages/<slug>/renders/NN-slug.mp4   (final, ready for normalize)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _common import fail, pick_video_encoder, resolve_ffmpeg

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())
FFMPEG = resolve_ffmpeg(CFG.get("ffmpeg_bin"))
OUT_W = CFG["output"]["width"]
OUT_H = CFG["output"]["height"]
OUT_FPS = CFG["output"]["fps"]
VID = CFG["video"]
TRK = CFG["tracking"]
FORCE_STYLE = (SKILL_ROOT / "config/force_style.txt").read_text().strip()


MP_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.task"
MP_MODEL_PATH = SKILL_ROOT / "config" / "blaze_face_short_range.task"


def _ensure_mediapipe_model() -> Path:
    if MP_MODEL_PATH.exists():
        return MP_MODEL_PATH
    import urllib.request

    print("  [first run] downloading mediapipe blaze_face model...", file=sys.stderr)
    urllib.request.urlretrieve(MP_MODEL_URL, MP_MODEL_PATH)
    return MP_MODEL_PATH


def sample_face_positions(
    src: Path, seg_start: float, seg_end: float, src_w: int, src_h: int
) -> list[tuple[float, float]]:
    """Return [(t_abs, cx_src)] sampled at SAMPLE_FPS using MediaPipe BlazeFace
    (new Tasks API). Falls back to OpenCV Haar if MediaPipe fails to load."""
    import cv2

    samples: list[tuple[float, float]] = []
    last_cx = src_w / 2.0

    detector = None
    use_mediapipe = TRK.get("detector", "mediapipe") == "mediapipe"
    if use_mediapipe:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            model_path = _ensure_mediapipe_model()
            options = mp_vision.FaceDetectorOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp_vision.RunningMode.IMAGE,
                min_detection_confidence=0.5,
            )
            detector = mp_vision.FaceDetector.create_from_options(options)
        except Exception as e:
            print(f"  [warn] MediaPipe init failed ({e}), falling back to Haar", file=sys.stderr)
            detector = None

    haar = None
    if detector is None:
        haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    cap = cv2.VideoCapture(str(src))
    t = seg_start
    dt = 1.0 / TRK["sample_fps"]
    while t < seg_end + dt:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        if detector is not None:
            import mediapipe as mp

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_img)
            if result.detections:
                best = max(
                    result.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height
                )
                bb = best.bounding_box
                last_cx = float(bb.origin_x + bb.width / 2.0)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = haar.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(TRK["min_face_size"], TRK["min_face_size"]),
            )
            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                last_cx = x + w / 2.0
        samples.append((t, last_cx))
        t += dt
    cap.release()
    if detector is not None:
        detector.close()
    return samples


def smooth_trajectory(samples: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Moving average over SMOOTH_WINDOW_S seconds."""
    import statistics

    win = max(1, int(round(TRK["smooth_window_s"] * TRK["sample_fps"])))
    smoothed: list[tuple[float, float]] = []
    for i, (ta, _cx) in enumerate(samples):
        lo = max(0, i - win // 2)
        hi = min(len(samples), i + win // 2 + 1)
        smoothed.append((ta, statistics.mean(p[1] for p in samples[lo:hi])))
    return smoothed


def cx_at(smoothed: list[tuple[float, float]], t_abs: float) -> float:
    """Linear interp."""
    if t_abs <= smoothed[0][0]:
        return smoothed[0][1]
    if t_abs >= smoothed[-1][0]:
        return smoothed[-1][1]
    for i in range(len(smoothed) - 1):
        t0, x0 = smoothed[i]
        t1, x1 = smoothed[i + 1]
        if t0 <= t_abs <= t1:
            f = (t_abs - t0) / (t1 - t0) if t1 > t0 else 0
            return x0 + f * (x1 - x0)
    return smoothed[-1][1]


def render_cut_singlepass(
    src: Path,
    seg_start: float,
    seg_end: float,
    out_video: Path,
    srt: Path | None = None,
) -> None:
    """Render a vertical cut in ONE ffmpeg pass.

    Combines what used to be three steps:
      (1) encode the tracked vertical frames to H.264
      (2) mux the source audio in (``-c:v copy``)
      (3) re-encode with the ``subtitles`` filter for burn-in

    Steps (1) and (3) both did a full H.264 encode, so the old pipeline
    paid for a second encode and accumulated generation loss. Single-pass
    fuses everything into one encode:

      - input 0 = raw BGR frames piped from this Python process (already
                  tracked + cropped to OUT_W × OUT_H)
      - input 1 = the source MP4 (seekable; we cut out the audio for the
                  segment using -ss/-to on the input side)
      - filter  = ``subtitles=<srt>:force_style=...`` applied to input 0
                  (skipped when ``srt is None``)
      - output  = mapped from raw frames + source audio, encoded once

    On Apple Silicon ``pick_video_encoder`` picks ``h264_videotoolbox``,
    which is ~6-10× faster than libx264 at indistinguishable quality for
    1080p talking-head content.
    """
    import cv2

    cap = cv2.VideoCapture(str(src))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  source {src_w}x{src_h}", file=sys.stderr)

    print(f"  pass 1: sampling face positions @ {TRK['sample_fps']} fps...", file=sys.stderr)
    samples = sample_face_positions(src, seg_start, seg_end, src_w, src_h)
    smoothed = smooth_trajectory(samples)
    print(
        f"  collected {len(samples)} samples, smoothed over ±{TRK['smooth_window_s']}s",
        file=sys.stderr,
    )

    new_w = int(round(src_w * (OUT_H / src_h)))
    new_w -= new_w % 2
    print(
        f"  scaled to {new_w}x{OUT_H}, crop window 1080w (range x∈[0,{new_w - OUT_W}])",
        file=sys.stderr,
    )

    total_frames = int(round((seg_end - seg_start) * OUT_FPS))

    # Build the filter graph. With an SRT we burn it on input 0; without,
    # we pass the raw frames through unchanged.
    vf_args: list[str] = []
    if srt is not None:
        # ffmpeg parses force_style as ASS key=value pairs separated by commas;
        # those commas need to be escaped inside the filter graph.
        style_esc = FORCE_STYLE.replace(",", r"\,")
        # Single-quote the whole filter expression so the colon in ``subtitles=``
        # isn't read as a filter separator.
        vf_args = ["-vf", f"subtitles={srt}:force_style='{style_esc}'"]

    encoder_args = pick_video_encoder(VID)

    cmd = [
        FFMPEG,
        "-y",
        # Input 0: raw BGR frames piped from cv2 below.
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{OUT_W}x{OUT_H}",
        "-r",
        str(OUT_FPS),
        "-i",
        "-",
        # Input 1: source video, audio segment only.
        "-ss",
        str(seg_start),
        "-to",
        str(seg_end),
        "-i",
        str(src),
        # Map: video from raw frames (0), audio from source (1).
        "-map",
        "0:v",
        "-map",
        "1:a",
        *vf_args,
        *encoder_args,
        # BT.709 color tags so macOS Preview / QuickTime render properly
        # (without these, Preview shows a blank/black canvas for vertical clips).
        "-color_range",
        "tv",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_video),
    ]

    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    print(f"  pass 2: rendering {total_frames} frames (single-pass)...", file=sys.stderr)
    cap.set(cv2.CAP_PROP_POS_MSEC, seg_start * 1000)
    for fi in range(total_frames):
        ok, frame = cap.read()
        if not ok:
            break
        t_abs = seg_start + fi / OUT_FPS
        scaled = cv2.resize(frame, (new_w, OUT_H), interpolation=cv2.INTER_AREA)
        cx_src = cx_at(smoothed, t_abs)
        cx_scaled = cx_src * (new_w / src_w)
        crop_x = int(round(cx_scaled - OUT_W / 2))
        crop_x = max(0, min(new_w - OUT_W, crop_x))
        crop = scaled[:, crop_x : crop_x + OUT_W]
        ff.stdin.write(crop.tobytes())
        if fi % 90 == 0:
            print(f"    frame {fi}/{total_frames} (t={t_abs:.1f}s, x={crop_x})", file=sys.stderr)
    ff.stdin.close()
    rc = ff.wait()
    cap.release()
    if rc != 0:
        fail(
            f"ffmpeg saiu com código {rc} ao renderizar {out_video.name}",
            hint="rode com FFMPEG_BIN apontando pra um build com libass e reveja o stderr",
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    ap.add_argument("--no-subs", action="store_true", help="render without burning subtitles")
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    src = msg_dir / "source.mp4"
    cuts = json.loads((msg_dir / "cuts_proposed.json").read_text())
    cut = cuts[args.cut_index - 1]
    n = cut.get("n", args.cut_index)
    slug = cut["slug"]
    seg_start = float(cut["start"])
    seg_end = float(cut["end"])

    renders = msg_dir / "renders"
    renders.mkdir(exist_ok=True)
    final = renders / f"{n:02d}-{slug}.mp4"

    srt: Path | None = None
    if not args.no_subs:
        srt = msg_dir / "srts" / f"{n:02d}-{slug}.srt"
        if not srt.exists():
            fail(
                f"SRT não encontrado: {srt}",
                hint=f"rode primeiro: ./scripts/06_build_srt.py {args.slug} {args.cut_index}",
            )

    print(f"[render] cut #{n} '{slug}' {seg_start:.2f}-{seg_end:.2f}s", file=sys.stderr)
    render_cut_singlepass(src, seg_start, seg_end, final, srt=srt)

    print(
        json.dumps(
            {
                "ok": True,
                "path": str(final),
                "size_mb": round(final.stat().st_size / (1024 * 1024), 1),
                "duration_s": round(seg_end - seg_start, 2),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
