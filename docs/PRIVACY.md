# Privacy & data handling

**English** · [Português](PRIVACY.pt.md) · [Español](PRIVACY.es.md)

Sermon Cuts is a local-first pipeline. The default workflow keeps your
sermon video and audio entirely on your computer. This document is the
honest answer to *"if I run this, who gets to see what?"*.

---

## TL;DR for pastors

- **Your video file never leaves your computer** under any provider.
- **Your audio leaves your computer ONLY** if you choose
  `--provider=groq` for transcription.
- **The transcript text** is sent to your AI editor (Claude, Cursor,
  etc.) when you ask it to propose cuts — same as any prompt you'd
  paste manually.
- **The final rendered MP4** stays local until you upload it yourself.

For maximum privacy: use `--provider=youtube` for transcription and
**do not** pass `--use-llm` to the SRT scrub. Everything else is local.

---

## What data each pipeline step touches

### `01_ingest.py` — getting the source video

| Source you give it | What leaves your machine |
|---|---|
| YouTube URL | URL is queried by `yt-dlp` to download the video. Standard YouTube traffic. |
| Local `.mp4` file | Nothing. File is symlinked or copied to `memory/messages/<slug>/source.mp4`. |

### `02_transcribe.py` — getting words with timestamps

| `--provider=` | What leaves your machine |
|---|---|
| `youtube` (default) | The YouTube URL is queried via `yt-dlp` to download the auto-caption VTT file. **No audio is uploaded.** Captions are parsed locally. |
| `groq` | The full sermon audio is extracted to a temp WAV file and uploaded to Groq's Whisper-large-v3 API for transcription. See [Groq's privacy policy](https://groq.com/privacy-policy/). |

### `03_vad_segments.py` — finding natural pauses

100% local. Runs [silero-vad](https://github.com/snakers4/silero-vad) on
the audio in-process. **No data leaves your machine.**

### `04_propose_cuts.py` — asking the AI for cut suggestions

This script itself does NOT call any API — it just prepares the
transcript and VAD data for your AI editor to read.

When you (or your editor) then act on the prompt:
- **The transcript text + VAD candidate timestamps** are sent to your
  AI editor's provider (Anthropic, OpenAI, etc.) as part of the prompt.
- **No audio** is sent.
- The video file is not sent — only the text representation.

If your AI editor lets you choose a model (e.g. claude-haiku vs
claude-opus), you can use a smaller model for cost; the transcript
text shared is the same.

### `05_validate_cut.py` — checking a cut for clean boundaries

100% local. Reads transcript + VAD + cuts JSON, writes back to disk.

### `06_build_srt.py` — generating the subtitle file

100% local. No network access.

### `06b_scrub_srt.py` — linting the SRT for transcription errors

| Mode | What leaves your machine |
|---|---|
| Default (rule-based only) | Nothing. Regex patterns run locally. |
| `--use-llm` | The SRT text + a short prompt are sent to either Anthropic (if `ANTHROPIC_API_KEY` is set) or Groq (if `GROQ_API_KEY` is set). |
| `--agent-review` | Nothing automatically. Writes a structured prompt for your interactive AI editor to read. |

### `07_render_track.py` — face-tracking and burning subtitles

100% local. MediaPipe runs in-process. On first run, downloads the
BlazeFace model (~10 MB) from `storage.googleapis.com/mediapipe-models/`
— after that, no network access.

### `08_audio_normalize.py` — leveling audio to -14 LUFS

100% local. ffmpeg's `loudnorm` filter does everything.

### `09_trim_silences.py` — optional dead-air removal

100% local.

---

## The privacy-maximal recipe

If you want **zero data leaving your machine** beyond the YouTube URL
itself, run:

```bash
# Transcribe locally (or via YouTube VTT — which is just URL lookup)
./scripts/02_transcribe.py <slug> --provider=youtube

# Run cut proposal yourself, reading the transcript manually instead
# of via Claude/Cursor — or use a local LLM (ollama, llama.cpp) instead

# Skip --use-llm on scrub
./scripts/06b_scrub_srt.py <slug> <n>     # no --use-llm flag

# Renders are local by design
./scripts/07_render_track.py <slug> <n>
./scripts/08_audio_normalize.py <slug> <n>
```

If your source is a local `.mp4` (not YouTube), the URL lookup goes
away too — **fully air-gapped** from start to finish.

---

## What's stored on your machine

The pipeline writes everything to two directories on your computer:

```
sources/<slug>/source.mp4          # or symlink to your original
memory/messages/<slug>/
├── transcript.json                # word-level timestamps
├── vad.json                       # pause/speech segments
├── cuts_proposed.json             # the AI's cut proposals
├── corrections.txt                # your per-sermon SRT corrections
├── srts/NN-slug.srt              # the burned subtitle files
└── (no audio file is stored separately)

renders/<slug>/
└── NN-slug.mp4                    # final vertical clips
```

All of this stays on your machine. The pipeline never uploads any of it
to a remote server. If you want a backup, you're responsible for it
(see the CLAUDE.md ritual for one approach: rsync to an external drive
or iCloud).

---

## What is NOT collected

The pipeline contains **zero telemetry**. No analytics, no error
reporting, no usage stats. It does not phone home. The only network
calls are the ones listed in this document, all triggered by your
explicit command-line flags.

---

## Provider-specific notes

### Groq Whisper

When you opt in via `--provider=groq`:
- The full audio chunk is uploaded.
- Per Groq's [policy](https://groq.com/privacy-policy/), they retain
  inputs for a short period for abuse monitoring; they do not (as of
  this writing) use API inputs to train models.
- If you're handling sensitive pastoral conversations (counseling,
  prayer recordings), consider whether the convenience is worth it.

### Anthropic / OpenAI (via your AI editor)

When you use Claude Code, Cursor, etc.:
- You're already governed by their existing privacy terms.
- Transcript text is sent — no audio.
- Their retention and training policies apply.

### YouTube (yt-dlp)

When you give a YouTube URL:
- The URL is queried.
- For `--provider=youtube`, only the auto-caption file is downloaded.
- For `--provider=groq`, the video is downloaded locally (so it can be
  re-encoded to audio).
- No personal data of yours is sent to YouTube beyond what your IP
  already reveals.

---

## Questions

Open an issue on [GitHub](https://github.com/onetogregorio/sermon-cuts/issues)
or contact via [netogregorio.com](https://netogregorio.com).

---

Written by [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
