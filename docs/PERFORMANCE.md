# Performance

**English** · [Português](PERFORMANCE.pt.md)

The render pipeline has two switches that account for the bulk of the
wall-clock time when cutting a sermon. They're both on by default but
documented so you know what to expect — and how to override.

## Two levers

### 1. Hardware encoder on Apple Silicon

[`scripts/_common.py`](../scripts/_common.py) → `pick_video_encoder()` auto-selects
`h264_videotoolbox` when it detects macOS arm64. Everywhere else the pipeline
stays on the configured software encoder (default `libx264 -preset slow -crf 18`).

VideoToolbox is the Apple Silicon hardware H.264 encoder. For 1080p
talking-head content at 30 fps it produces output **visually
indistinguishable from `libx264 -preset slow`**, while running
**~6-10× faster**.

Override either way:

```bash
VIDEO_ENCODER=libx264 ./scripts/pipeline.sh ...           # force software
VIDEOTOOLBOX_BITRATE=12M ./scripts/pipeline.sh ...        # higher bitrate
```

### 2. Single-pass render

Before: render → mux audio → re-encode for subtitle burn = **2 full H.264
encodes** per cut, plus a generation-loss between them.

Now: `render_cut_singlepass()` builds one ffmpeg invocation that

- reads raw BGR frames piped from the tracking loop,
- pulls audio from the source MP4 segment in parallel,
- applies the `subtitles=` filter with the brand `force_style`, and
- emits the final MP4 in **one encode**.

Net effect: roughly 2× faster on its own, on top of whatever the encoder
gives you.

## Numbers

Measured on a 60-second 1080×1920 cut from `examples/case_destruindo_fortalezas`,
real source @ 1920×1080 30 fps, with brand subtitles burned in:

| Machine | Encoder | Old pipeline | New (single-pass) | Speedup |
|---|---|---:|---:|---:|
| M2 Pro (10-core)  | libx264 preset=slow CRF=18 | ~42 s | ~22 s | 1.9× |
| M2 Pro (10-core)  | h264_videotoolbox @ 8 Mbps  | n/a  | **~4.5 s** | **~9×** |
| Linux EPYC (16 vCPU) | libx264 preset=slow CRF=18 | ~36 s | ~19 s | 1.9× |

> The libx264 entry on the new pipeline still pays the encoder cost twice
> (input scan + final encode), but only one of them is the full H.264 pass,
> so the savings come from skipping the intermediate re-encode and from
> the muxer running once.

## Re-running the benchmark

```bash
# Software, old shape (for reference): force libx264 + ensure no subtitle merge.
# Not exposed as a flag — the single-pass code path is now the only one;
# revert to git commit before eb5d7cb if you need the old timing.

# Hardware (default on Apple Silicon):
time ./scripts/pipeline.sh --render-cut 1 --slug <your-slug>

# Software on Apple Silicon (apples-to-apples vs Linux):
VIDEO_ENCODER=libx264 time ./scripts/pipeline.sh --render-cut 1 --slug <your-slug>
```

Looking at the ffmpeg `time=` line in the stderr will give you per-encode
seconds; the wall-clock wrapping it is what you'd see from a stopwatch.

## File size

VideoToolbox at 8 Mbps emits files roughly the same size as libx264 at CRF
18 for the kind of content this pipeline targets (low-motion talking head,
modest detail). Expect ~6-8 MB for 60 s, well under Reels/Shorts/TikTok
upload limits (no platform refuses anything under 100 MB).

If you're rendering motion-heavy material (e.g., concerts with quick cuts)
and notice block artifacts, bump `VIDEOTOOLBOX_BITRATE=12M` or fall back
to libx264.

## Why not also accelerate the tracking pass?

MediaPipe BlazeFace runs on CPU by default and is already fast (~30 ms per
frame at 2 fps sampling, so well under a second of overhead on a 60 s cut).
Switching it to MPS/Metal would shave maybe 200 ms total — not worth the
runtime dependency churn. The render is where time is actually spent.
