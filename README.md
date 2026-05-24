# sermon-cuts

> Pipeline that turns a long preaching/teaching video into ready-to-publish
> vertical short clips (Reels / Shorts / TikTok). YouTube URL in → curated
> vertical cuts with burned-in branded subtitles out.

Built specifically for portuguese-language sermons, but the pipeline is
language-agnostic (`--language=en`, `pt`, etc).

---

## What it does

```
YouTube URL ──┐
              ├──► transcribe (YouTube VTT or Groq Whisper, word-level)
              ├──► VAD silence detection (silero-vad)  →  natural cut boundaries
              ├──► LLM proposes N cuts with full narrative arcs + score
              │
   [you curate which to render]
              │
              ├──► validate (no cut ending in "porque...", "mas...", etc)
              ├──► chunk subtitles (3-4 words, function-word-aware, brand style)
              ├──► face-tracking smooth pan crop  →  vertical 1080×1920
              ├──► burn subtitles (gold Outfit Black + black outline + footer)
              └──► LUFS normalize to -14 (Insta/TikTok/Reels)
```

Output: `memory/messages/<slug>/renders/NN-cut_slug.mp4` ready for upload.

---

## Why

Short-form vertical clips drive most reach for preaching content today,
but cutting a 30-min sermon into 8-10 great verticals takes hours per
sermon if done by hand in CapCut/Premiere. This tool gets it to ~5
minutes of human curation per sermon, automating:

- Transcription with word-level timestamps
- Finding cut boundaries that don't snap mid-word (via VAD)
- Identifying segments with complete narrative arcs (LLM-assisted)
- Vertical reframing that follows the speaker (face tracking + smoothing)
- Branded subtitles that look like a designer made them
- Audio normalization to platform-standard loudness

---

## Install

**System dependencies:**

```bash
# macOS
brew install ffmpeg yt-dlp python@3.12
# Optional but recommended for high-quality subtitle rendering:
# install the Outfit Black font from https://fonts.google.com/specimen/Outfit
```

**Python deps:**

```bash
pip install -r requirements.txt
```

**Optional:** put your `GROQ_API_KEY` in `~/.env` if you want to use
`--provider=groq` for higher-accuracy transcription (the default uses
YouTube auto-captions, which is free and instant).

---

## Quickstart

```bash
# 1. Ingest + transcribe + VAD + prepare cut proposal
./scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# 2. (Claude or you) reads transcript + VAD and writes
#    memory/messages/<slug>/cuts_proposed.json
#    Use the prompt at prompts/propose_cuts.md
#    See examples/ for what good cut proposals look like.

# 3. Render the cuts you approved
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug vinde
```

Final cuts land at:
```
memory/messages/<slug>/renders/01-cut_slug.mp4
memory/messages/<slug>/renders/02-cut_slug.mp4
...
```

---

## Pipeline scripts

Each script does one thing. They can be run standalone or via
`scripts/pipeline.sh`.

| Script | Purpose |
|---|---|
| `01_ingest.py` | YouTube URL OR local path → `source.mp4` + `meta.json` |
| `02_transcribe.py` | YouTube VTT (default) or Groq Whisper → `transcript.json` |
| `03_vad_segments.py` | silero-vad pauses → `vad.json` (cut candidates) |
| `04_propose_cuts.py` | Pack inputs for the LLM cut proposal step |
| `05_validate_cut.py` | Reject/auto-extend cuts that end mid-thought |
| `06_build_srt.py` | Brand-style SRT (3-4 words, function-word shift, sentence case) |
| `07_render_track.py` | MediaPipe face track → smooth pan crop → burn subtitle |
| `08_audio_normalize.py` | pyloudnorm to -14 LUFS (Insta/TikTok/Reels) |
| `pipeline.sh` | Orchestrate all of the above |

See [`docs/PIPELINE.md`](docs/PIPELINE.md) for full walkthrough.

---

## Customizing brand style

Edit `config/force_style.txt` (ASS subtitle string) and
`config/render_defaults.yaml` (output dims, FPS, encoder, audio target).

The default style is:

- Font: **Outfit Black** (gold `#fbc531`, black outline `0.8`)
- Position: bottom-center, `MarginV=50` (above Insta UI strip)
- Sentence case, never UPPERCASE
- 3-4 words per cue, max ~20 chars, function-word-aware breaks

See `CLAUDE.md` for the design rationale.

---

## Transcription: YouTube vs Groq

The default `--provider=youtube` reads YouTube auto-captions via yt-dlp.
**Pros:** free, instant (~3 seconds), no API key needed.
**Cons:** Whisper-grade errors on rare/proper words (we've seen e.g.
"superestimamos a Mas" — missed a word).

The fallback `--provider=groq` uses Groq Whisper-large-v3.
**Pros:** much more accurate, fast (~30s per 10-min audio).
**Cons:** needs `GROQ_API_KEY` in `~/.env` (free tier is generous).

Both produce the same JSON schema; the rest of the pipeline doesn't care.

See [`docs/TRANSCRIPTION_NOTES.md`](docs/TRANSCRIPTION_NOTES.md) for more.

---

## Example output

See [`examples/`](examples/) for a sample cut and the cut proposals from
the sermon used to build this tool (Mateus 11: "Vinde a mim").

---

## Use as a Claude Code skill

If you use [Claude Code](https://claude.com/claude-code), this repo
includes a `SKILL.md` you can register so Claude invokes the pipeline
naturally when you say things like *"corta essa pregação"* or paste a
YouTube link.

```bash
# Symlink approach (single source of truth)
mkdir -p ~/.claude/skills/sermon-cuts
ln -s "$(pwd)/scripts" ~/.claude/skills/sermon-cuts/scripts
ln -s "$(pwd)/config"  ~/.claude/skills/sermon-cuts/config
ln -s "$(pwd)/prompts" ~/.claude/skills/sermon-cuts/prompts
cp SKILL.md ~/.claude/skills/sermon-cuts/SKILL.md
```

After that, Claude will recognize this skill and use the pipeline
end-to-end on conversational requests.

---

## License

MIT — see [`LICENSE`](LICENSE).

Built by [@netogregorio](https://github.com/netogregorio) with
[Claude Code](https://claude.com/claude-code).
