# Sermon Cuts — containerized pipeline.
#
# Build:
#   docker build -t sermon-cuts .
#
# Usage (process + render in one shot):
#   docker run --rm \
#     -v "$(pwd)/out:/work/memory/messages" \
#     -e GROQ_API_KEY=$GROQ_API_KEY \
#     sermon-cuts <youtube-url-or-mounted-mp4>
#
# Process a local mp4:
#   docker run --rm \
#     -v "$(pwd)/in:/in:ro" \
#     -v "$(pwd)/out:/work/memory/messages" \
#     sermon-cuts /in/sermon.mp4
#
# Notes
#   • Volumes: ``/work/memory/messages`` is where every render lands; mount
#     a host folder there so the cut files survive ``docker rm``.
#   • GROQ_API_KEY is optional; without it the pipeline picks --provider=local
#     (faster-whisper) or --provider=youtube as appropriate.
#   • The Outfit font is baked in — the container has it on disk so libass
#     resolves the brand style without any host setup.
#   • The image is built on python:3.12-slim and adds ffmpeg via apt (Debian
#     ships ffmpeg with libass).

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── system deps ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg yt-dlp ca-certificates curl unzip fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Brand font: Outfit Black, dropped where fontconfig will find it.
RUN mkdir -p /usr/share/fonts/truetype/outfit \
    && curl -fsSL "https://fonts.google.com/download?family=Outfit" -o /tmp/outfit.zip \
    && unzip -oq /tmp/outfit.zip -d /usr/share/fonts/truetype/outfit \
    && rm /tmp/outfit.zip \
    && fc-cache -f

# ── Python deps ───────────────────────────────────────────────────────────
WORKDIR /work
COPY requirements.txt .
# Pin pip and pre-install — keeps the layer cacheable across edits to /work below.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── skill files ───────────────────────────────────────────────────────────
COPY scripts/ /work/scripts/
COPY config/  /work/config/
COPY prompts/ /work/prompts/
COPY SKILL.md /work/SKILL.md

# Symlink so the scripts find themselves at the path they assume
# (~/.claude/skills/sermon-cuts/) — same shape the host install uses.
RUN mkdir -p /root/.claude/skills \
    && ln -s /work /root/.claude/skills/sermon-cuts

# /work/memory/messages is where renders live. Declare it as a volume so the
# image-default storage doesn't grow unbounded if someone forgets to mount.
VOLUME ["/work/memory/messages"]

ENTRYPOINT ["bash", "/work/scripts/pipeline.sh"]
CMD ["doctor"]
