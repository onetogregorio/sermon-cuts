"""Shared helpers for sermon-cuts pipeline scripts."""

from __future__ import annotations

import os
import platform
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


# ─── video encoder selection ──────────────────────────────────────────────


def pick_video_encoder(config: dict) -> list[str]:
    """Return the ffmpeg encoder argv chunk best suited to this machine.

    On Apple Silicon we prefer ``h264_videotoolbox`` (hardware-accelerated,
    ~6-10× faster than libx264 ``preset=slow`` at indistinguishable quality
    for 1080p talking-head content). Everywhere else we fall through to
    whatever the config says (typically libx264 CRF).

    Override either way with ``VIDEO_ENCODER=libx264`` / ``=h264_videotoolbox``
    in the env — useful for benchmarking or when ffmpeg lacks VideoToolbox.

    The function returns a list of ffmpeg arguments meant to splice straight
    into a Popen/run argv, e.g.::

        cmd = [FFMPEG, "-y", "-i", "-", *pick_video_encoder(CFG["video"]),
               "-movflags", "+faststart", out]
    """
    forced = os.environ.get("VIDEO_ENCODER", "").strip().lower()
    encoder = config.get("encoder", "libx264")
    if forced:
        encoder = forced
    elif platform.system() == "Darwin" and platform.machine() == "arm64" and encoder == "libx264":
        encoder = "h264_videotoolbox"

    pix_fmt = config.get("pix_fmt", "yuv420p")

    if encoder == "h264_videotoolbox":
        # Hardware encoder: tune via bitrate target instead of CRF.
        # 8 Mbps is overkill for 1080p talking-head but file size is still
        # small (~6-8 MB for 60s) and it leaves room for fast-cut B-roll
        # without artifacting.
        bitrate = os.environ.get("VIDEOTOOLBOX_BITRATE", "8M")
        return [
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            bitrate,
            "-pix_fmt",
            pix_fmt,
        ]

    # Software encoder (libx264): keep the preset/crf tunables from config.
    preset = config.get("preset", "slow")
    crf = str(config.get("crf", 18))
    return [
        "-c:v",
        encoder,
        "-preset",
        preset,
        "-crf",
        crf,
        "-pix_fmt",
        pix_fmt,
    ]


# ─── user-visible data paths (sources / renders) ──────────────────────────


_SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"


def repo_root() -> Path:
    """The real filesystem path of the cloned repo, regardless of how the
    user reached it (direct clone, ~/.claude/skills/ symlinks, CI checkout).

    Resolution order:
      1. ``SERMON_CUTS_REPO`` env var if set.
      2. ``Path(__file__).resolve().parent.parent`` — this module always
         lives at ``<repo>/scripts/_common.py``, so its grandparent is
         always the real repo root, with or without an install symlink
         in the path. Works in CI (no skill installed) and locally
         (skill symlinks resolve through to here).
    """
    env = os.environ.get("SERMON_CUTS_REPO", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def config_dir() -> Path:
    """``<repo>/config/`` — pipeline config files, prompts, style presets,
    function-word lists. Read by every script."""
    return repo_root() / "config"


def prompts_dir() -> Path:
    """``<repo>/prompts/`` — agent system prompts (propose_cuts, scrub_srt)."""
    return repo_root() / "prompts"


def user_data_dir() -> Path:
    """Default user-data root, OS-aware. Where renders + sources live by
    default when no env override is set.

    Rationale: the skill is meant to be installed once and used against
    many sermons over many years. Putting user data (raw videos, rendered
    cuts) inside the cloned code repo couples data lifetime to the repo
    checkout — a ``git clean -fd`` or a re-clone would nuke months of
    sermons. So we default to a stable user-visible location:

      - macOS  → ``~/Movies/SermonCuts/``        (Movies.app sees it)
      - Linux  → ``$XDG_DATA_HOME/sermon-cuts``  or ``~/.local/share/sermon-cuts``
      - Other  → ``~/SermonCuts/``               (Windows, BSDs)

    Override with ``SERMON_CUTS_DATA_DIR`` to put everything elsewhere.
    """
    env = os.environ.get("SERMON_CUTS_DATA_DIR", "").strip()
    if env:
        return Path(env)
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Movies" / "SermonCuts"
    if system == "Linux":
        xdg = os.environ.get("XDG_DATA_HOME", "").strip()
        if xdg:
            return Path(xdg) / "sermon-cuts"
        return Path.home() / ".local" / "share" / "sermon-cuts"
    return Path.home() / "SermonCuts"


def _legacy_repo_dir(name: str) -> Path | None:
    """Return ``<repo>/<name>`` only if it exists with content — used as a
    transitional back-compat fallback for users who set up before we moved
    defaults out of the repo. Empty placeholder dirs (just .gitkeep) don't
    count. None means "no legacy data, use the new default"."""
    candidate = repo_root() / name
    if not candidate.exists():
        return None
    real_content = [
        p for p in candidate.iterdir()
        if p.name not in {".gitkeep", "README.md", ".DS_Store"}
    ]
    return candidate if real_content else None


def resolve_sources_dir() -> Path:
    """Where source .mp4 files live, organized by slug.

    Resolution order:
      1. ``SERMON_CUTS_SOURCES_DIR`` env var (absolute path override).
      2. Legacy ``<repo>/sources/`` if it already has slug content
         (back-compat for setups predating the user-data-dir move).
      3. ``user_data_dir() / "sources"`` — the new agnostic default.

    Each message gets its own subfolder: ``<dir>/<slug>/source.mp4`` plus
    any extras you drop alongside it.
    """
    env = os.environ.get("SERMON_CUTS_SOURCES_DIR", "").strip()
    if env:
        return Path(env)
    if legacy := _legacy_repo_dir("sources"):
        return legacy
    return user_data_dir() / "sources"


def resolve_renders_dir() -> Path:
    """Where final rendered cuts land, organized by slug.

    Resolution order:
      1. ``SERMON_CUTS_RENDERS_DIR`` env var (absolute path override).
      2. Legacy ``<repo>/renders/`` if it already has slug content.
      3. ``user_data_dir() / "renders"`` — the new agnostic default.

    Output path: ``<dir>/<slug>/NN-slug.mp4``.
    """
    env = os.environ.get("SERMON_CUTS_RENDERS_DIR", "").strip()
    if env:
        return Path(env)
    if legacy := _legacy_repo_dir("renders"):
        return legacy
    return user_data_dir() / "renders"


def resolve_messages_dir() -> Path:
    """Where per-message state (transcript.json, vad.json, srts/, meta.json,
    cuts_proposed.json, corrections.txt) lives.

    Default: ``<skill>/memory/messages/<slug>/`` when the skill install
    exists at ``~/.claude/skills/sermon-cuts/``. Otherwise (CI runs,
    direct-clone usage without the install symlinks) falls back to
    ``<repo>/memory/messages/``.

    Override with ``SERMON_CUTS_MESSAGES_DIR``.
    """
    env = os.environ.get("SERMON_CUTS_MESSAGES_DIR", "").strip()
    if env:
        return Path(env)
    if _SKILL_ROOT.exists():
        return _SKILL_ROOT / "memory/messages"
    return repo_root() / "memory/messages"


# ─── subtitle style preset selection ──────────────────────────────────────


def load_style_preset(subtitle_cfg: dict | None = None) -> str:
    """Resolve the libass ``force_style`` string for the burn-in pass.

    Lookup order (first match wins):
      1. ``SUBTITLE_PRESET`` env var — quick per-render override without
         touching any file.
      2. ``config/force_style.txt`` if present — advanced override that
         lets a power user pin a fully hand-tuned style.
      3. ``config/style_presets/<preset>.txt`` where ``<preset>`` comes
         from ``subtitle.preset`` in render_defaults.yaml (default
         ``arial-black``).
      4. ``config/style_presets/arial-black.txt`` as universal fallback.

    Reads config_dir() under the hood, which itself follows `__file__`
    to the real repo — works in CI without a skill install.
    """
    presets_dir = config_dir() / "style_presets"

    env_preset = os.environ.get("SUBTITLE_PRESET", "").strip()
    if env_preset:
        env_path = presets_dir / f"{env_preset}.txt"
        if env_path.exists():
            return env_path.read_text().strip()
        # Fall through silently to lower-priority sources rather than failing —
        # an unknown preset name shouldn't break a render.

    legacy = config_dir() / "force_style.txt"
    if legacy.exists() and legacy.stat().st_size > 0:
        return legacy.read_text().strip()

    preset = (subtitle_cfg or {}).get("preset") or "arial-black"
    preset_path = presets_dir / f"{preset}.txt"
    if not preset_path.exists():
        fallback = presets_dir / "arial-black.txt"
        if fallback.exists():
            return fallback.read_text().strip()
        # Last-ditch hardcoded default so a misconfigured install still renders.
        return (
            "FontName=Arial Black,FontSize=16,Bold=1,"
            "PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,"
            "BorderStyle=1,Outline=0.8,Shadow=0,Alignment=2,MarginV=50"
        )
    return preset_path.read_text().strip()
