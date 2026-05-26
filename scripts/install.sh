#!/usr/bin/env bash
# Sermon Cuts — one-liner installer.
#
# Idempotent: safe to re-run. Won't overwrite an existing .env, won't
# duplicate symlinks, won't re-clone an existing repo.
#
# Usage (from anywhere on a fresh machine):
#   curl -fsSL https://onetogregorio.github.io/sermon-cuts/install.sh | bash
#
# Or from a clone of the repo:
#   ./scripts/install.sh
#
# Override the clone location:
#   SERMON_CUTS_DIR=~/projects/sermon-cuts bash install.sh

set -euo pipefail

# Detect non-interactive invocation (`curl install.sh | bash`, CI, etc.).
# When TTY isn't available we can't prompt — the helpers below use this
# flag to silently fall back to defaults instead of letting `set -e`
# abort the script on the first read EOF.
NON_INTERACTIVE=0
if [ ! -t 0 ]; then
  NON_INTERACTIVE=1
fi

REPO_URL="https://github.com/onetogregorio/sermon-cuts.git"
SERMON_CUTS_DIR="${SERMON_CUTS_DIR:-$HOME/code/sermon-cuts}"
SKILL_DIR="$HOME/.claude/skills/sermon-cuts"

# ─── pretty output ────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN="\033[32m"; YEL="\033[33m"; RED="\033[31m"
  BOLD="\033[1m"; DIM="\033[2m"; RST="\033[0m"
else
  GREEN=""; YEL=""; RED=""; BOLD=""; DIM=""; RST=""
fi

say() { printf "${BOLD}%s${RST}\n" "$1"; }
ok()  { printf "  ${GREEN}✓${RST} %s\n" "$1"; }
note(){ printf "  ${DIM}→ %s${RST}\n" "$1"; }
warn(){ printf "  ${YEL}!${RST} %s\n" "$1"; }
die() { printf "  ${RED}✗${RST} %s\n" "$1" >&2; exit 1; }
ask() {
  local q="$1" default="${2:-n}" ans
  # When stdin isn't a TTY (script is piped: `curl ... | bash`), we can't
  # prompt the user — silently use the default so set -e doesn't kill us.
  if [ ! -t 0 ]; then
    [[ "$default" =~ ^[yY] ]]
    return $?
  fi
  read -r -p "  ❯ $q [y/N] " ans || ans=""
  ans="${ans:-$default}"
  [[ "$ans" =~ ^[yY] ]]
}

# Prompt for a string with a fallback default. Safe under `curl | bash`:
# returns the default without prompting when stdin isn't a TTY.
prompt() {
  local q="$1" default="${2:-}" var
  if [ ! -t 0 ]; then
    printf '%s' "$default"
    return 0
  fi
  read -r -p "  ❯ $q" var || var=""
  printf '%s' "${var:-$default}"
}

# ─── detect OS ────────────────────────────────────────────────────────────
say "1. Detectando sistema"
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *) die "Sistema não suportado: $OS (apenas macOS e Linux por enquanto)" ;;
esac
ok "$PLATFORM/$ARCH"

# ─── system deps ──────────────────────────────────────────────────────────
say "2. Dependências de sistema"

ensure_macos_deps() {
  if ! command -v brew >/dev/null 2>&1; then
    warn "Homebrew não está instalado"
    if ask "Instalar Homebrew agora?"; then
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
      die "Homebrew é necessário no macOS. Veja https://brew.sh"
    fi
  fi
  ok "Homebrew presente"

  local pkgs=(ffmpeg-full yt-dlp python@3.12)
  for pkg in "${pkgs[@]}"; do
    if brew list --formula "$pkg" >/dev/null 2>&1; then
      ok "$pkg já instalado"
    else
      note "instalando $pkg via brew (pode demorar uns minutos)"
      brew install "$pkg"
      ok "$pkg instalado"
    fi
  done
}

ensure_linux_deps() {
  if ! command -v apt-get >/dev/null 2>&1; then
    warn "Distribuição não-Debian detectada"
    note "Por favor instale manualmente: ffmpeg (com libass), yt-dlp, python3.12+, python3-venv"
    if ! ask "Continuar mesmo assim?"; then exit 1; fi
    return
  fi
  note "atualizando apt..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq ffmpeg python3 python3-pip python3-venv yt-dlp
  ok "ffmpeg, python3, yt-dlp instalados"
}

if [[ "$PLATFORM" == "macos" ]]; then
  ensure_macos_deps
else
  ensure_linux_deps
fi

# ─── clone or update repo ─────────────────────────────────────────────────
say "3. Repositório"
if [[ -d "$SERMON_CUTS_DIR/.git" ]]; then
  ok "já clonado em $SERMON_CUTS_DIR"
  note "fazendo git pull pra pegar updates"
  (cd "$SERMON_CUTS_DIR" && git pull --ff-only) || warn "git pull falhou — segue com a versão local"
else
  mkdir -p "$(dirname "$SERMON_CUTS_DIR")"
  note "clonando $REPO_URL em $SERMON_CUTS_DIR"
  git clone "$REPO_URL" "$SERMON_CUTS_DIR"
  ok "clonado"
fi

# ─── python venv + deps ───────────────────────────────────────────────────
say "4. Python venv + dependências"
cd "$SERMON_CUTS_DIR"
if [[ ! -d ".venv" ]]; then
  note "criando .venv com python3..."
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
note "pip install -r requirements.txt (silencioso)"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "deps Python instaladas no .venv"

# ─── symlink skill ────────────────────────────────────────────────────────
say "5. Skill ~/.claude/skills/sermon-cuts/"
mkdir -p "$SKILL_DIR"
for sub in scripts config prompts; do
  if [[ -L "$SKILL_DIR/$sub" ]]; then
    ok "$sub: symlink já existe"
  elif [[ -e "$SKILL_DIR/$sub" ]]; then
    warn "$SKILL_DIR/$sub existe e NÃO é symlink — pulando pra não destruir nada"
  else
    ln -s "$SERMON_CUTS_DIR/$sub" "$SKILL_DIR/$sub"
    ok "$sub: symlinkado"
  fi
done
if [[ -f "$SKILL_DIR/SKILL.md" ]]; then
  ok "SKILL.md já copiado"
else
  cp "$SERMON_CUTS_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
  ok "SKILL.md copiado"
fi

# ─── optional: Groq API key ───────────────────────────────────────────────
say "6. Groq Whisper (opcional, transcrição premium)"
ENV_FILE="$HOME/.env"
if [[ -f "$ENV_FILE" ]] && grep -q "^GROQ_API_KEY=" "$ENV_FILE"; then
  ok "GROQ_API_KEY já configurada em $ENV_FILE"
elif [[ -n "${GROQ_API_KEY:-}" ]]; then
  ok "GROQ_API_KEY já no shell env"
else
  note "abra https://console.groq.com/keys, crie uma chave (free tier funciona)"
  if ask "Adicionar GROQ_API_KEY no $ENV_FILE agora?"; then
    key="$(prompt "cole a chave (gsk_...): ")"
    if [[ "$key" =~ ^gsk_ ]]; then
      echo "GROQ_API_KEY=$key" >> "$ENV_FILE"
      ok "salvo em $ENV_FILE"
    else
      warn "chave não começa com gsk_ — não salvei"
    fi
  else
    note "pulando. Use --provider=youtube por padrão (auto-captions, grátis)"
  fi
fi

# ─── subtitle font preset ────────────────────────────────────────────────
say "7. Estilo de legenda — escolha uma fonte"
note "Default é Arial Black (sistema, sem download). Outfit Black baixa do Google."
echo "  1) arial-black     — Arial Black, universal (default)"
echo "  2) helvetica-bold  — Helvetica Bold, mais limpo (macOS-native)"
echo "  3) outfit-black    — Outfit Black, fonte display warm (requer download)"
font_choice="$(prompt "escolha [1-3, default 1]: " "1")"
case "${font_choice:-1}" in
  1) PRESET="arial-black"; DOWNLOAD_OUTFIT=0 ;;
  2) PRESET="helvetica-bold"; DOWNLOAD_OUTFIT=0 ;;
  3) PRESET="outfit-black"; DOWNLOAD_OUTFIT=1 ;;
  *) warn "opção inválida — usando arial-black"; PRESET="arial-black"; DOWNLOAD_OUTFIT=0 ;;
esac
ok "preset selecionado: $PRESET"

# Patch the YAML to use the chosen preset. We use a tiny Python one-liner
# because sed-on-YAML is fragile across platforms (BSD sed vs GNU sed).
python3 - "$SERMON_CUTS_DIR/config/render_defaults.yaml" "$PRESET" <<'PY'
import re, sys
path, preset = sys.argv[1], sys.argv[2]
text = open(path).read()
new = re.sub(r"^(\s*preset:\s*)[a-z-]+", rf"\g<1>{preset}", text, count=1, flags=re.MULTILINE)
open(path, "w").write(new)
PY

# Download Outfit only if the user picked outfit-black.
if [[ "$DOWNLOAD_OUTFIT" -eq 1 ]]; then
  FONT_INSTALLED=0
  for p in "$HOME/Library/Fonts/Outfit-Black.ttf" \
           "/Library/Fonts/Outfit-Black.ttf" \
           "$HOME/.local/share/fonts/Outfit-Black.ttf"; do
    [[ -f "$p" ]] && { FONT_INSTALLED=1; break; }
  done
  if [[ "$FONT_INSTALLED" -eq 1 ]]; then
    ok "Outfit Black já instalada"
  else
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT
    curl -fsSL "https://fonts.google.com/download?family=Outfit" -o "$TMP_DIR/outfit.zip"
    if [[ "$PLATFORM" == "macos" ]]; then
      DEST="$HOME/Library/Fonts"
    else
      DEST="$HOME/.local/share/fonts"
      mkdir -p "$DEST"
    fi
    unzip -oq "$TMP_DIR/outfit.zip" -d "$DEST"
    [[ "$PLATFORM" == "linux" ]] && fc-cache -f "$DEST" >/dev/null 2>&1 || true
    ok "Outfit Black instalada em $DEST"
  fi
fi

# ─── MediaPipe models (pre-download so first render doesn't need network) ──
# Google moves these URLs occasionally (the old /1/ paths 404'd as of
# mid-2024; current canonical is /latest/). Pre-downloading at install
# time means a failed runtime fetch can't silently degrade face tracking
# to Haar cascade on a user's first cut — and they're tiny (~10 MB total).
say "8. Modelos MediaPipe (face + pose tracking)"
MP_DIR="$SERMON_CUTS_DIR/config"
MP_FACE_URL="https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
MP_POSE_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
for spec in "blaze_face_short_range.tflite:$MP_FACE_URL" \
            "pose_landmarker_lite.task:$MP_POSE_URL"; do
  fname="${spec%%:*}"
  url="${spec#*:}"
  dest="$MP_DIR/$fname"
  if [[ -f "$dest" ]]; then
    ok "$fname já presente"
  else
    if curl -fsSL "$url" -o "$dest"; then
      ok "$fname baixado"
    else
      warn "$fname falhou — face tracking pode cair pro Haar no primeiro render"
      rm -f "$dest"
    fi
  fi
done

# ─── final doctor ─────────────────────────────────────────────────────────
say "9. Health check"
python3 "$SERMON_CUTS_DIR/scripts/doctor.py" || true

printf "\n${GREEN}${BOLD}Instalação concluída.${RST}\n"
printf "Primeiro corte:\n"
printf "  ${DIM}cd $SERMON_CUTS_DIR${RST}\n"
printf "  ${DIM}source .venv/bin/activate${RST}\n"
printf "  ${BOLD}./scripts/pipeline.sh https://youtube.com/watch?v=...${RST}\n\n"
