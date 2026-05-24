# Instalação

[English](INSTALL.md) · **Português** · [Español](INSTALL.es.md)

## Dependências do sistema

### macOS

```bash
brew install ffmpeg yt-dlp python@3.12

# Opcional: instalar a fonte Outfit Black (usada para queima de legenda)
# Baixe em https://fonts.google.com/specimen/Outfit
# Mova o .ttf para ~/Library/Fonts/
```

Você precisa do ffmpeg compilado com `libass`, `libx264` e `libfontconfig` (o
padrão `brew install ffmpeg` já inclui).

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y ffmpeg python3 python3-pip yt-dlp

# Opcional: instalar a Outfit Black (usada na queima de legenda)
mkdir -p ~/.local/share/fonts
curl -L https://fonts.google.com/download?family=Outfit > /tmp/outfit.zip
unzip /tmp/outfit.zip -d ~/.local/share/fonts/
fc-cache -f -v
```

### Fallback de fonte

A Outfit é **opcional**. Se não estiver instalada, o libass cai pra fonte
sans-serif padrão do sistema (Helvetica Bold no macOS, DejaVu Sans ou similar
no Linux). Os cortes renderizam normalmente, mas não vão bater com o brand
style descrito em [STYLE.md](STYLE.md). Instale a Outfit se a identidade
visual importa pra você.

## Dependências Python

```bash
pip install -r requirements.txt
```

Se estiver em um sistema com PEP 668 (distribuições Python mais novas), use um
virtualenv ou passe `--break-system-packages`.

## Opcional: API Groq para transcrição de maior qualidade

A transcrição padrão usa auto-legendas do YouTube (grátis, sem chave).
Para usar Groq Whisper-large-v3 (mais preciso, ~30s por 10min de áudio):

```bash
# Obtenha uma chave API gratuita em https://console.groq.com/keys
echo 'GROQ_API_KEY=gsk_sua_chave_aqui' >> ~/.env
```

Depois rode qualquer script com `--provider=groq`.

## Opcional: registro de skill do Claude Code

Se você usa Claude Code:

```bash
mkdir -p ~/.claude/skills/sermon-cuts
ln -s "$(pwd)/scripts" ~/.claude/skills/sermon-cuts/scripts
ln -s "$(pwd)/config"  ~/.claude/skills/sermon-cuts/config
ln -s "$(pwd)/prompts" ~/.claude/skills/sermon-cuts/prompts
cp SKILL.md ~/.claude/skills/sermon-cuts/SKILL.md
```

Claude agora invocará essa skill em pedidos como "cut this sermon",
"corta essa pregação", ou URLs do YouTube com intenção de corte.

## Verificar instalação

```bash
python3 -c "import cv2, mediapipe, soundfile, silero_vad, pyloudnorm, yt_dlp, groq, yaml; print('all imports OK')"
ffmpeg -version | head -1
yt-dlp --version
```

Se todos os três imprimirem sem erros, está pronto.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
