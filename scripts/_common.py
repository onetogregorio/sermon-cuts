"""Shared helpers for sermon-cuts pipeline scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

# ─── error formatting ─────────────────────────────────────────────────────

_TTY = sys.stderr.isatty()
_RED = "\033[31m" if _TTY else ""
_YEL = "\033[33m" if _TTY else ""
_DIM = "\033[2m" if _TTY else ""
_BOLD = "\033[1m" if _TTY else ""
_RST = "\033[0m" if _TTY else ""


def fail(
    msg: str, *, hint: str | None = None, url: str | None = None, exit_code: int = 1
) -> NoReturn:
    """Print a friendly, actionable error and exit.

    Format (PT-BR friendly, English-technical mix matching the project tone):
        ✗ <msg>
          → <hint>
          → veja: <url>

    All output goes to stderr; the message is colorized when the stream is a TTY.
    """
    print(f"{_RED}✗{_RST} {_BOLD}{msg}{_RST}", file=sys.stderr)
    if hint:
        print(f"  {_YEL}→{_RST} {hint}", file=sys.stderr)
    if url:
        print(f"  {_DIM}→ veja: {url}{_RST}", file=sys.stderr)
    sys.exit(exit_code)


def warn(msg: str, *, hint: str | None = None) -> None:
    """Print a non-fatal warning to stderr."""
    print(f"{_YEL}!{_RST} {msg}", file=sys.stderr)
    if hint:
        print(f"  {_DIM}→ {hint}{_RST}", file=sys.stderr)


# ─── schema versioning ────────────────────────────────────────────────────

SCHEMA_VERSION = 1
"""Bump whenever the shape of transcript.json / cuts_proposed.json /
vad.json changes in a non-backward-compatible way."""


def check_schema(payload: dict, *, filename: str) -> None:
    """Warn (but don't fail) if a JSON we read was written under a different
    schema version. Bumping ``SCHEMA_VERSION`` in this module signals to all
    pipeline scripts that older artifacts may need regeneration."""
    seen = payload.get("_schema_version")
    if seen is None:
        # Old file from before versioning landed. Tolerate silently.
        return
    if seen != SCHEMA_VERSION:
        warn(
            f"{filename} foi gerado com schema v{seen}, atual é v{SCHEMA_VERSION}",
            hint="rode o passo anterior do pipeline com --force pra regerar",
        )


# ─── binary discovery ─────────────────────────────────────────────────────


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
