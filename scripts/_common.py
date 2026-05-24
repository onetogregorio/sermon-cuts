"""Shared helpers for sermon-cuts pipeline scripts."""
from __future__ import annotations
import os
from pathlib import Path


def resolve_ffmpeg(config_value: str | None = None) -> str:
    """Pick the ffmpeg binary to use, with libass support preferred.

    Priority:
      1. ``FFMPEG_BIN`` environment variable — explicit user override.
      2. ``config_value`` — usually ``CFG["ffmpeg_bin"]`` from render_defaults.yaml.
      3. ``/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`` — Homebrew's full build,
         which (unlike the default ``ffmpeg`` formula since v8.x) includes
         libass. Required for the ``subtitles`` filter used by ``07_render_track``.
      4. ``"ffmpeg"`` — fall back to whatever is on PATH.

    Symptom this was added for: ``[AVFilterGraph] No such filter: 'subtitles'``
    from Homebrew's default ffmpeg 8.x build (libass was dropped). Either set
    ``FFMPEG_BIN=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`` in your shell, or
    install ``brew install ffmpeg-full`` and we'll auto-detect it.
    """
    if env := os.environ.get("FFMPEG_BIN"):
        return env
    if config_value:
        return config_value
    hb_full = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg")
    if hb_full.exists():
        return str(hb_full)
    return "ffmpeg"
