# Installation

**English** · [Português](INSTALL.pt.md) · [Español](INSTALL.es.md)

## System dependencies

### macOS

```bash
brew install ffmpeg yt-dlp python@3.12

# Optional: install Outfit Black font (used by subtitle burn)
# Download from https://fonts.google.com/specimen/Outfit
# Move the .ttf to ~/Library/Fonts/
```

You need ffmpeg compiled with `libass`, `libx264`, and `libfontconfig` (the
default `brew install ffmpeg` includes these).

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y ffmpeg python3 python3-pip yt-dlp

# Optional: install Outfit Black (used by subtitle burn)
mkdir -p ~/.local/share/fonts
curl -L https://fonts.google.com/download?family=Outfit > /tmp/outfit.zip
unzip /tmp/outfit.zip -d ~/.local/share/fonts/
fc-cache -f -v
```

### Font fallback

Outfit is **optional**. If it's not installed on the system, libass falls
back to the system's default sans-serif (Helvetica Bold on macOS, DejaVu Sans
or similar on Linux). Cuts will still render, but they won't match the brand
style described in [STYLE.md](STYLE.en.md). Install Outfit if the brand look
matters to you.

## Python deps

```bash
pip install -r requirements.txt
```

If you're on a system with PEP 668 (newer Python distributions), use a
virtualenv or pass `--break-system-packages`.

## Optional: Groq API for higher-quality transcription

The default transcription uses YouTube auto-captions (free, no key needed).
To use Groq Whisper-large-v3 (more accurate, ~30s per 10min audio):

```bash
# Get a free API key at https://console.groq.com/keys
echo 'GROQ_API_KEY=gsk_your_key_here' >> ~/.env
```

Then run any script with `--provider=groq`.

## Optional: Claude Code skill registration

If you use Claude Code:

```bash
mkdir -p ~/.claude/skills/sermon-cuts
ln -s "$(pwd)/scripts" ~/.claude/skills/sermon-cuts/scripts
ln -s "$(pwd)/config"  ~/.claude/skills/sermon-cuts/config
ln -s "$(pwd)/prompts" ~/.claude/skills/sermon-cuts/prompts
cp SKILL.md ~/.claude/skills/sermon-cuts/SKILL.md
```

Claude will now invoke this skill on requests like "cut this sermon",
"corta essa pregação", or YouTube URLs paired with cutting intent.

## Verify install

```bash
python3 -c "import cv2, mediapipe, soundfile, silero_vad, pyloudnorm, yt_dlp, groq, yaml; print('all imports OK')"
ffmpeg -version | head -1
yt-dlp --version
```

If all three print without errors, you're set.
