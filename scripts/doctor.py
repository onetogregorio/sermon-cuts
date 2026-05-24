#!/usr/bin/env python3
"""Health check for sermon-cuts.

Verifies the system has every binary, Python dep, font, and config the
pipeline needs. Prints a colorized report (✓ green / ! yellow / ✗ red)
with an actionable hint next to anything that's not in good shape.

Exit code is the count of red items, so ``pipeline.sh doctor && pipeline.sh ...``
short-circuits when the environment is broken.

Usage:
    doctor.py
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import _BOLD, _DIM, _RED, _RST, _TTY, _YEL, resolve_ffmpeg

GREEN = "\033[32m" if _TTY else ""
SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"

# Tally of issues, by severity.
_red = 0
_yellow = 0


def ok(name: str, detail: str = "") -> None:
    extra = f" {_DIM}({detail}){_RST}" if detail else ""
    print(f"  {GREEN}✓{_RST} {name}{extra}")


def warn(name: str, hint: str) -> None:
    global _yellow
    _yellow += 1
    print(f"  {_YEL}!{_RST} {_BOLD}{name}{_RST}")
    print(f"      {_DIM}→ {hint}{_RST}")


def bad(name: str, hint: str) -> None:
    global _red
    _red += 1
    print(f"  {_RED}✗{_RST} {_BOLD}{name}{_RST}")
    print(f"      {_DIM}→ {hint}{_RST}")


def section(title: str) -> None:
    print(f"\n{_BOLD}{title}{_RST}")


# ─── checks ───────────────────────────────────────────────────────────────


def check_ffmpeg() -> None:
    ffmpeg = resolve_ffmpeg()
    if not shutil.which(ffmpeg) and not Path(ffmpeg).exists():
        bad(
            "ffmpeg",
            "instale com `brew install ffmpeg-full` (macOS) ou `apt install ffmpeg` (Linux)",
        )
        return
    # Confirm it has libass (needed by the subtitles filter).
    try:
        out = subprocess.check_output(
            [ffmpeg, "-filters"], stderr=subprocess.STDOUT, text=True, timeout=10
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        bad("ffmpeg", "binário existe mas não responde a `-filters`; reinstale o ffmpeg")
        return
    if "subtitles" not in out:
        bad(
            "ffmpeg (libass)",
            "esse build NÃO tem o filtro `subtitles`. Use `brew install ffmpeg-full` "
            "ou exporte FFMPEG_BIN apontando pra um build com libass",
        )
        return
    # Version line for the detail.
    ver = subprocess.check_output([ffmpeg, "-version"], text=True).splitlines()[0]
    ok("ffmpeg", ver.split("Copyright")[0].strip())


def check_yt_dlp() -> None:
    if not shutil.which("yt-dlp"):
        bad("yt-dlp", "instale com `brew install yt-dlp` ou `pip install yt-dlp`")
        return
    try:
        ver = subprocess.check_output(["yt-dlp", "--version"], text=True).strip()
        ok("yt-dlp", f"v{ver}")
    except subprocess.CalledProcessError:
        warn("yt-dlp", "binário presente mas falhou em --version")


def check_python_deps() -> None:
    required = [
        ("yaml", "pyyaml"),
        ("groq", "groq"),
        ("mediapipe", "mediapipe"),
        ("cv2", "opencv-python-headless"),
        ("numpy", "numpy"),
        ("soundfile", "soundfile"),
        ("silero_vad", "silero-vad"),
    ]
    missing = []
    for mod, pkg in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        bad(
            "Python deps", f"faltando: {', '.join(missing)}. Rode `pip install -r requirements.txt`"
        )
    else:
        ok("Python deps", "todas as 7 importáveis")


def check_subtitle_preset() -> None:
    """Report which subtitle style preset is active + whether the font it
    asks for is actually installed."""
    import os

    import yaml

    cfg_path = SKILL_ROOT / "config/render_defaults.yaml"
    try:
        cfg = yaml.safe_load(cfg_path.read_text())
    except Exception:
        bad("subtitle preset", f"could not read {cfg_path}")
        return

    preset_name = os.environ.get("SUBTITLE_PRESET") or cfg.get("subtitle", {}).get(
        "preset", "arial-black"
    )
    preset_file = SKILL_ROOT / "config/style_presets" / f"{preset_name}.txt"
    if not preset_file.exists():
        bad("subtitle preset", f"preset '{preset_name}' não tem .txt em config/style_presets/")
        return

    style = preset_file.read_text().strip()
    # Extract FontName= from the force_style string.
    font_name = "(unknown)"
    for pair in style.split(","):
        if pair.startswith("FontName="):
            font_name = pair.split("=", 1)[1]
            break

    # Probe whether the font is reachable. Arial Black / Helvetica are on
    # virtually every system; Outfit needs manual install.
    font_installed = _font_resolvable(font_name)
    detail = f"preset={preset_name} font={font_name}"
    if font_installed:
        ok("subtitle preset", detail)
    else:
        warn(
            f"subtitle preset ({detail})",
            f"libass não vai achar '{font_name}' — vai cair pra system fallback. "
            f"Pra instalar: https://fonts.google.com/specimen/{font_name.replace(' ', '+')}",
        )


def _font_resolvable(font_name: str) -> bool:
    """Best-effort check that ``font_name`` is reachable by libass.

    We check:
      • obvious filesystem paths (macOS user/system fonts, Linux user fonts);
      • ``fc-list`` when fontconfig is present.

    System fonts like ``Arial Black`` and ``Helvetica`` won't show up as
    .ttf files in user folders, so we treat them as available when fc-list
    knows them OR when we just can't verify (assume the system has them).
    """
    # Filesystem first (covers manually-installed fonts like Outfit Black).
    safe = font_name.replace(" ", "")
    candidates = [
        Path.home() / "Library/Fonts" / f"{font_name}.ttf",
        Path.home() / "Library/Fonts" / f"{safe}.ttf",
        Path.home() / "Library/Fonts" / f"{safe}-Black.ttf",
        Path("/Library/Fonts") / f"{font_name}.ttf",
        Path("/System/Library/Fonts") / f"{safe}.ttc",
        Path.home() / ".local/share/fonts" / f"{font_name}.ttf",
    ]
    if any(p.exists() for p in candidates):
        return True
    try:
        out = subprocess.check_output(["fc-list", ":family"], text=True, timeout=5)
        return font_name.lower() in out.lower()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # If fc-list isn't available, assume the font is system-resolvable
        # (Arial Black and Helvetica ship on every supported OS).
        return font_name.lower() in {"arial black", "helvetica", "helvetica bold"}


def check_groq_key() -> None:
    if os.environ.get("GROQ_API_KEY"):
        ok("GROQ_API_KEY", "set no env")
        return
    env_files = [Path.home() / ".env", Path.cwd() / ".env"]
    for ef in env_files:
        if ef.exists() and "GROQ_API_KEY=" in ef.read_text():
            ok("GROQ_API_KEY", f"em {ef}")
            return
    warn(
        "GROQ_API_KEY",
        "não configurada (opcional). Sem ela --provider=groq não funciona; "
        "use --provider=youtube ou local. Pegue em https://console.groq.com/keys",
    )


def check_local_whisper() -> None:
    try:
        import faster_whisper  # noqa: F401

        ok("faster-whisper", "instalado (--provider=local disponível)")
    except ImportError:
        warn(
            "faster-whisper",
            "não instalado (opcional). Sem ele --provider=local não funciona — "
            "instale com `pip install faster-whisper` se quiser transcrição offline.",
        )


def check_skill_symlinks() -> None:
    expected = ["scripts", "config", "prompts", "SKILL.md"]
    if not SKILL_ROOT.exists():
        bad(
            "skill symlink",
            f"{SKILL_ROOT} não existe. Rode o install prompt ou crie symlinks "
            "manualmente conforme docs/INSTALL.md",
        )
        return
    missing = [name for name in expected if not (SKILL_ROOT / name).exists()]
    if missing:
        bad("skill symlink", f"faltando dentro de {SKILL_ROOT}: {', '.join(missing)}")
        return
    ok("skill symlink", str(SKILL_ROOT))


def check_platform_encoder() -> None:
    """Inform the user if the hardware encoder will kick in (FYI only)."""
    system = platform.system()
    machine = platform.machine()
    if system == "Darwin" and machine == "arm64":
        ok("hardware encoder", "h264_videotoolbox disponível (Apple Silicon)")
    else:
        ok("video encoder", f"libx264 (CPU) — sistema: {system}/{machine}")


# ─── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    print(f"{_BOLD}sermon-cuts doctor{_RST}  {_DIM}— health check{_RST}")

    section("System binaries")
    check_ffmpeg()
    check_yt_dlp()

    section("Python environment")
    check_python_deps()

    section("Skill installation")
    check_skill_symlinks()

    section("Subtitle style")
    check_subtitle_preset()

    section("Optional but recommended")
    check_groq_key()
    check_local_whisper()
    check_platform_encoder()

    print()
    if _red:
        print(
            f"{_RED}{_red} problema(s) crítico(s){_RST}, "
            f"{_YEL}{_yellow} aviso(s){_RST} — corrija o vermelho antes de rodar a pipeline."
        )
        sys.exit(_red)
    if _yellow:
        print(f"{GREEN}tudo essencial OK{_RST}, {_YEL}{_yellow} aviso(s) opcionais{_RST}.")
        sys.exit(0)
    print(f"{GREEN}tudo verde. pronto pra cortar.{_RST}")


if __name__ == "__main__":
    main()
