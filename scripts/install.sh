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
  read -r -p "  ❯ $q [y/N] " ans || ans=""
  ans="${ans:-$default}"
  [[ "$ans" =~ ^[yY] ]]
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
    read -r -p "  ❯ cole a chave (gsk_...): " key
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

# ─── optional: Outfit font ────────────────────────────────────────────────
say "7. Fonte Outfit Black (opcional, brand style)"
FONT_INSTALLED=0
for p in "$HOME/Library/Fonts/Outfit-Black.ttf" \
         "/Library/Fonts/Outfit-Black.ttf" \
         "$HOME/.local/share/fonts/Outfit-Black.ttf"; do
  [[ -f "$p" ]] && { FONT_INSTALLED=1; break; }
done
if [[ "$FONT_INSTALLED" -eq 1 ]]; then
  ok "Outfit Black já instalada"
elif ask "Baixar e instalar Outfit Black agora?"; then
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
  ok "Outfit instalada em $DEST"
else
  note "pulado. libass cai pra Helvetica/DejaVu (cortes renderizam, sem brand style)"
fi

# ─── final doctor ─────────────────────────────────────────────────────────
say "8. Health check"
python3 "$SERMON_CUTS_DIR/scripts/doctor.py" || true

printf "\n${GREEN}${BOLD}Instalação concluída.${RST}\n"
printf "Primeiro corte:\n"
printf "  ${DIM}cd $SERMON_CUTS_DIR${RST}\n"
printf "  ${DIM}source .venv/bin/activate${RST}\n"
printf "  ${BOLD}./scripts/pipeline.sh https://youtube.com/watch?v=...${RST}\n\n"
