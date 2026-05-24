# Glossary

**English** · [Português](GLOSSARY.pt.md) · [Español](GLOSSARY.es.md)

Plain-language definitions for terms you'll see in the docs, prompts,
and error messages. Skim this once and the rest of the project reads
easier.

---

## Pipeline anatomy

**Pipeline** — the chain of scripts (`01_ingest` → `02_transcribe` →
… → `08_audio_normalize`) that turns a long sermon video into short
vertical clips. Each script does one thing and writes to disk before
handing off.

**Skill** — the wrapper that lets AI coding agents (Claude Code,
Cursor, Cline, Aider, etc.) invoke the pipeline conversationally. It's
just a `SKILL.md` file + the `scripts/` folder. When you say "corta
essa pregação" in Claude Code, it reads `SKILL.md` and runs the right
commands.

**Slug** — the short, computer-friendly name for one sermon (no
spaces, no accents). Examples: `vinde`, `derrubando_fortalezas`,
`mateus_11_sunday`. Every sermon gets its own slug and its own working
directory.

**Working directory** — `memory/messages/<slug>/`. Where everything
about one sermon lives: transcript, cut proposals, subtitle files,
correction notes.

---

## Cut anatomy

**Cut** — a single short clip produced from the sermon. A 30-minute
sermon typically yields 8–12 cuts of 25–60 seconds each.

**Hook** — the opening line of a cut. The first 1–2 seconds that
either pulls the viewer in or loses them. Strong hooks are concrete,
specific, surprising.

**Development** — what happens in the middle of a cut. The story
unfolds, the point gets built, the analogy gets explored.

**Conclusion / payoff** — the closing line. Where the cut lands.
Should resolve what the hook promised — a punchline, an application, a
biblical quote.

**Coherence score** — 0–10 rating the LLM assigns each proposed cut
based on whether the hook + development + conclusion fits together
cleanly and reads as a self-contained idea.

---

## Subtitles

**SRT** — `.srt` (SubRip Text) is the standard subtitle file format.
Plain text with cue numbers, timestamps, and text. Sermon Cuts writes
one SRT per cut.

**Cue** — one entry in an SRT. Typically 3–4 words shown together on
screen for 0.5–2 seconds.

**Function word** — short words like "de", "para", "com", "que",
"mas", "porque" that connect ideas but don't carry meaning alone.
Cues should never end on these — the eye gets stuck waiting for the
next word. The chunker has logic to shift them forward.

**Forbidden ending** — a function word at the end of a cue. The
pipeline tries to prevent these via shifting; what it can't shift gets
flagged for human review.

**Hook boost** — the `{\fs22\b1}` ASS markup auto-added to the first
cue of each cut. Makes the first line slightly bigger + bold during
the burn-in so it pulls the eye on the scroll.

**Burn-in** — the act of permanently embedding subtitles into the
video pixels (vs. shipping the SRT separately). Once burned, the
subtitle can't be turned off.

**libass** — the library ffmpeg uses to render ASS/SRT subtitles into
video. Must be compiled into your ffmpeg build for the `subtitles`
filter to work.

**`force_style`** — the styling string passed to libass that controls
font, color, outline, size, position. Lives in
`config/style_presets/*.txt`.

---

## Audio

**LUFS** (Loudness Units Full Scale) — the modern measure of perceived
loudness. Instagram, TikTok, Reels, and YouTube all normalize to about
-14 LUFS, which is why we target that.

**True peak (dBTP)** — the actual peak signal level after audio
reconstruction. Different from sample peak. We target -1.5 dBTP so
there's headroom and no clipping.

**Clipping** — when audio exceeds the maximum representable level and
gets cut off, producing a distorted "crunching" sound. The
true-peak-limited normalizer prevents this.

**Loudnorm** — ffmpeg's EBU R128 loudness normalization filter.
Industry standard for broadcasting and streaming.

---

## Video tracking

**Face tracking** — sampling face position frame-by-frame and using it
to decide where to crop the vertical frame. Keeps the speaker centered
even when they walk across stage.

**MediaPipe** — Google's open-source ML toolkit. The pipeline uses
MediaPipe's BlazeFace short-range face detector and pose landmarker
(for shoulder fallback when face detection misses).

**VAD (Voice Activity Detection)** — algorithm that identifies which
parts of audio contain speech vs. silence. Sermon Cuts uses
[silero-vad](https://github.com/snakers4/silero-vad) to find natural
pauses where cuts can land without splitting mid-word.

**Pan smoothing** — averaging face X positions over a 2.5s window so
the crop doesn't jitter as detections wobble frame-to-frame. Gives the
final video a "cinematic" pan feel.

**Crop window** — the 1080-wide window that gets cut from the source
frame (typically 1920 wide) to produce the vertical 1080×1920 output.

---

## Video tech

**BT.709** — the color space standard for HD video. macOS Preview
refuses to display H.264 videos cleanly if their BT.709 color metadata
isn't explicitly tagged. The pipeline tags it on every render.

**H.264 / libx264** — the video codec used for output. Standard for
web and social platforms. CRF 18 (default) = visually lossless.

**Preset (slow/fast/etc)** — libx264's encoding speed vs. file size
tradeoff. `slow` = smaller file at the same quality, takes longer.
`fast` = larger file, encodes quicker.

**MP4 / faststart** — the container format. `+faststart` reorders the
file so playback can begin before the full download — essential for
streaming.

---

## Transcription

**Whisper** — OpenAI's open-source speech-to-text model. Groq hosts a
fast inference API for the large variant (`whisper-large-v3`).

**Groq** — third-party inference provider with very fast Whisper API.
Free tier covers most personal use.

**VTT** (Web Video Text Tracks) — YouTube's subtitle format. Sermon
Cuts parses YouTube's auto-generated VTT files when you use
`--provider=youtube`.

**yt-dlp** — open-source command-line tool to download videos and
captions from YouTube and many other platforms.

---

## Files & paths

**`sources/<slug>/source.mp4`** — your raw sermon video (or a symlink
to it).

**`memory/messages/<slug>/`** — working artifacts for one sermon
(transcript, VAD, cut proposals, SRTs).

**`renders/<slug>/NN-slug.mp4`** — pipeline output. Vertical, captioned,
audio-normalized.

**`edit/cuts/<Sermon Name>/`** — your curation folder for finals (per
the CLAUDE.md ritual; personal convention, gitignored).

**`config/`** — pipeline defaults, function-word lists, style presets,
optional correction dictionaries.

**`prompts/`** — system prompts sent to the LLM during cut proposal
and SRT scrub.

---

By [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
