# Instalación

[English](INSTALL.md) · [Português](INSTALL.pt.md) · **Español**

## Dependencias del sistema

### macOS

```bash
brew install ffmpeg yt-dlp python@3.12

# Opcional: instalar la fuente Outfit Black (usada para quemar subtítulos)
# Descargue de https://fonts.google.com/specimen/Outfit
# Mueva el .ttf a ~/Library/Fonts/
```

Necesita ffmpeg compilado con `libass`, `libx264` y `libfontconfig` (el
predeterminado `brew install ffmpeg` los incluye).

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y ffmpeg python3 python3-pip yt-dlp \
                    fonts-dejavu-core  # respaldo si Outfit no está instalada
# Instale Outfit Black:
mkdir -p ~/.local/share/fonts
curl -L https://fonts.google.com/download?family=Outfit > /tmp/outfit.zip
unzip /tmp/outfit.zip -d ~/.local/share/fonts/
fc-cache -f -v
```

## Dependencias Python

```bash
pip install -r requirements.txt
```

Si está en un sistema con PEP 668 (distribuciones Python más nuevas), use un
virtualenv o pase `--break-system-packages`.

## Opcional: API Groq para transcripción de mayor calidad

La transcripción predeterminada usa subtítulos automáticos de YouTube (gratis, sin clave).
Para usar Groq Whisper-large-v3 (más preciso, ~30s por 10min de audio):

```bash
# Obtenga una clave API gratuita en https://console.groq.com/keys
echo 'GROQ_API_KEY=gsk_su_clave_aqui' >> ~/.env
```

Luego ejecute cualquier script con `--provider=groq`.

## Opcional: registro de habilidad Claude Code

Si usa Claude Code:

```bash
mkdir -p ~/.claude/skills/sermon-cuts
ln -s "$(pwd)/scripts" ~/.claude/skills/sermon-cuts/scripts
ln -s "$(pwd)/config"  ~/.claude/skills/sermon-cuts/config
ln -s "$(pwd)/prompts" ~/.claude/skills/sermon-cuts/prompts
cp SKILL.md ~/.claude/skills/sermon-cuts/SKILL.md
```

Claude ahora invocará esta habilidad en solicitudes como "cut this sermon",
"corta esa predicación", o URLs de YouTube con intención de corte.

## Verificar instalación

```bash
python3 -c "import cv2, mediapipe, soundfile, silero_vad, pyloudnorm, yt_dlp, groq, yaml; print('all imports OK')"
ffmpeg -version | head -1
yt-dlp --version
```

Si los tres imprimen sin errores, está listo.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
