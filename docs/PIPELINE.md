# Pipeline walkthrough

**English** · [Português](PIPELINE.pt.md) · [Español](PIPELINE.es.md)

Each script writes to `memory/messages/<slug>/` and is idempotent (re-running
is safe and skips done work unless `--force`).

## 01_ingest.py

```bash
./scripts/01_ingest.py <youtube-url-or-local-path> [--slug SLUG]
```

YouTube URL → uses yt-dlp to download best quality up to 1080p as MP4.
Local file → symlinks (or copies if symlink fails).

Writes:
- `memory/messages/<slug>/source.mp4`
- `memory/messages/<slug>/meta.json` (URL/path/title/duration)

Slug derivation: from YouTube title or filename (slugified to snake_case).
Override with `--slug`.

## 02_transcribe.py

```bash
./scripts/02_transcribe.py <slug> [--provider=youtube|groq] [--language=pt]
```

### YouTube (default, free, instant)

Calls `yt-dlp --write-auto-subs --skip-download` to grab the VTT auto-caption
file YouTube generates for every public video. Parses inline word-level
timestamps from the VTT (those `<HH:MM:SS.mmm>` tags between words).

### Groq (paid-ish, higher quality)

Extracts audio (mono 16kHz WAV), uploads to Groq Whisper-large-v3 with
`timestamp_granularities=["word"]`. Returns word-level timestamps.
Needs `GROQ_API_KEY` in env.

Output (same shape for both):

```json
{
  "words": [
    {"text": "Eu", "start": 1.95, "end": 2.12, "type": "word"},
    {"text": " ", "start": 2.12, "end": 2.13, "type": "spacing"},
    ...
  ],
  "language": "pt",
  "_provider": "youtube-vtt"  // or "groq-whisper-large-v3"
}
```

## 03_vad_segments.py

```bash
./scripts/03_vad_segments.py <slug> [--min-silence 0.5]
```

Runs [silero-vad](https://github.com/snakers4/silero-vad) on the source
audio (resampled to 16kHz mono). Detects speech segments → derives the
silences between them → marks the midpoint of each silence ≥ 0.5s as a
**candidate cut point** (places where a cut won't snap mid-word/mid-breath).

Output:

```json
{
  "speech": [{"start": 0.34, "end": 12.18}, ...],
  "silences": [{"start": 12.18, "end": 13.05, "duration": 0.87}, ...],
  "candidate_cut_points": [12.18, 28.71, ...]
}
```

## 04_propose_cuts.py

```bash
./scripts/04_propose_cuts.py <slug>
```

Packages transcript + VAD into a single `propose_input.json` and prints
the paths the LLM (Claude) should read, plus the prompt at
`prompts/propose_cuts.md`. **This script does not call an LLM** — it just
prepares inputs.

The LLM is expected to write proposed cuts to
`memory/messages/<slug>/cuts_proposed.json`.

The expected schema for each cut:

```json
{
  "n": 1,
  "slug": "filha_no_mercado",
  "start": 92.40,
  "end": 165.10,
  "duration_s": 72.7,
  "theme": "Relação vs missão — ilustração da filha no mercado",
  "hook": "Eu gosto de uma ilustração muito boa...",
  "development": "...",
  "conclusion": "Jesus pede que a gente vá COM ele, não pra ficar n'Ele",
  "coherence_score": 9.2,
  "tags": ["ilustracao", "relacionamento_com_deus"],
  "vad_aligned": true
}
```

See `prompts/propose_cuts.md` for the full rubric.

## 05_validate_cut.py

```bash
./scripts/05_validate_cut.py <slug> <cut_index> [--write-back] [--max-extend-s 8]
```

Confirms the cut's last word isn't a forbidden ending (configurable in
`config/render_defaults.yaml` — e.g. "porque", "mas", "que", "para", "com",
"de"). If it is, tries to extend the end to the next VAD candidate cut
point within `max-extend-s` seconds where the word is no longer forbidden.

`--write-back` patches the cut in `cuts_proposed.json`.

## 06_build_srt.py

```bash
./scripts/06_build_srt.py <slug> <cut_index>
```

Generates a brand-styled SRT from the transcript words in the cut's range:

- 3-4 words per cue, max ~20 chars (configurable)
- Splits on punctuation (`. ! ?` hard, `, ; :` soft if cue has ≥3 words)
- Splits on ≥0.5s pause if cue has ≥3 words
- Function-word-aware shift: if a cue ends with "para"/"com"/"que"/etc.,
  shifts it to the next cue (so cues never end on a function word)
- Capitalizes the first cue
- Strips trailing soft punctuation from cue text

Writes `memory/messages/<slug>/srts/NN-slug.srt`.

## 06b_scrub_srt.py

```bash
./scripts/06b_scrub_srt.py <slug> <cut_index> [--agent-review]
                                              [--use-llm]
                                              [--auto-apply]
                                              [--dry-run]
                                              [--corrections PATH]
```

Lint pass that runs **between `06_build_srt` and `07_render_track`**,
scanning the SRT for the YouTube-auto-caption error patterns we see most
often (dropped sentence boundaries, hesitation duplications, theological
term misspellings). Lets you fix transcription errors before burn-in
instead of after — saves a full re-encode per typo.

### What it looks for

1. **`dropped_word_boundary`** — a function word (em / que / de / etc.)
   immediately before a capitalized non-proper-noun. YouTube ate a word
   at a sentence boundary.
       `"do que Mas não"`  ←  was actually  `"do que nós. Mas não"`
   Whitelists common Bible characters/places and Portuguese pronouns so
   `"em Cristo"` and `"para Ele"` don't false-positive.

2. **`immediate_repetition`** — `\b(\w+)\s+\1\b` filtered to known
   hesitations (a, o, um, uma, que, eu, ele, ela, …) and short words.
   Skips stylistic repetition separated by commas like `"cansa, cansa"`.

3. **`forbidden_ending`** — re-checks the
   `cut_validation.forbid_endings` list per cue (not just at the cut
   boundary like `05_validate_cut.py` does). Reports only; the fix
   usually means shifting the trailing word into the next cue, which
   the human should do.

4. **`dictionary`** — if `memory/messages/<slug>/corrections.txt`
   exists, applies `wrong=right` pairs automatically (one per line,
   `#` for comments). Useful for recurring fixes:
   ```
   Quisto=Cristo
   Espirito=Espírito
   ```

### Three review paths

| Path | When to use |
|---|---|
| **`--agent-review`** (default in non-TTY with suspects) | The orchestrator (Claude Code / Cursor / …) is reading stdout. 06b emits structured JSON with prev/next cue text, a word-level transcript snippet around each suspect, and the path to `prompts/scrub_srt.md`. The agent reads the prompt, decides fixes, applies them via its Edit tool, and resumes the pipeline with `--skip-scrub`. |
| **`--use-llm`** | Standalone runs (cron, nightly, no agent attached). Calls Anthropic Claude (prefers `ANTHROPIC_API_KEY`) or Groq Llama (`GROQ_API_KEY` fallback). The same `prompts/scrub_srt.md` becomes the system prompt; the LLM returns a `{fixes: [{cue, new_text, reason}]}` JSON that we apply on the SRT. |
| **`--auto-apply`** | Rule-only, confidence ≥ 0.85. Effectively just collapses hesitation repetitions silently. Cheapest mode. |

### Other modes

| Flag | Behavior |
|---|---|
| (none, TTY)     | interactive review — prompts `y/n/edit/skip` per suspect |
| `--dry-run`     | only reports, never writes the SRT |

`pipeline.sh` integrates this step automatically (interactive on TTY,
`--agent-review` JSON in non-TTY so the orchestrating agent can act).
Skip with `--skip-scrub`:

```bash
./scripts/pipeline.sh --render-cuts 1,2 --slug my_msg --skip-scrub
```

Writes back to `memory/messages/<slug>/srts/NN-slug.srt` in place. JSON
report goes to stdout:

```json
{
  "ok": true,
  "srt": "...",
  "suspects": [
    {"cue": 27, "tc": "00:00:36,080", "text": "do que Mas não",
     "pattern": "dropped_word_boundary",
     "suggestion": "do que. Mas não",
     "confidence": 0.75, "applied": false}
  ],
  "applied_count": 0,
  "dry_run": false
}
```

## 07_render_track.py

```bash
./scripts/07_render_track.py <slug> <cut_index> [--no-subs]
```

Two-pass render:

**Pass 1 — face position sampling.** At 2 fps (default), runs MediaPipe
BlazeFace short-range detector on the source frame. Records the center-X
of the largest detected face. Falls back to OpenCV Haar cascade if
MediaPipe fails.

**Smoothing.** Moving average over 2.5s (5 samples) of face X positions
removes detection jitter and gives a cinematic feel.

**Pass 2 — render frame-by-frame.** For each source frame:
1. Scale to height 1920 preserving aspect (1920×1080 → 3413×1920)
2. Interpolate smoothed X for the current frame timestamp
3. Crop 1080×1920 centered on that X (clamped to frame bounds)
4. Pipe raw BGR frames to ffmpeg for H.264 encoding (CRF 18 preset slow)

**Audio mux.** Combines encoded video with the source audio segment.

**Subtitle burn.** Applies ffmpeg `subtitles=` filter with `force_style`
from `config/force_style.txt`. Skip with `--no-subs`.

Writes `memory/messages/<slug>/renders/NN-slug.mp4`.

## 08_audio_normalize.py

```bash
./scripts/08_audio_normalize.py <slug> <cut_index> [--target-lufs -14] [--in-place]
```

Measures integrated loudness with pyloudnorm (ITU-R BS.1770-4), applies
gain to hit target LUFS. Re-encodes audio to AAC 192k, copies video stream.

`--in-place` overwrites the original render. Otherwise writes a
`.normalized.mp4` sibling.

## pipeline.sh

Orchestrator:

```bash
# Ingest + transcribe + VAD + prepare propose-input
./scripts/pipeline.sh "https://youtube.com/watch?v=XXX"

# Render specific cut indices end-to-end (validate + SRT + render + normalize)
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug my_sermon

# Just re-burn subtitles (after correcting transcription) without re-tracking
./scripts/pipeline.sh --reburn-srt 3 --slug my_sermon
```

## Per-message directory layout

After a complete run:

```
memory/messages/<slug>/
├── source.mp4              # symlink or download
├── meta.json               # URL/title/duration
├── transcript.json         # word-level with type=word/spacing
├── vad.json                # speech segments + cut candidates
├── propose_input.json      # combined input for the LLM
├── cuts_proposed.json      # LLM output (you curate this)
├── srts/
│   └── NN-slug.srt
└── renders/
    └── NN-slug.mp4         # final, ready to upload
```
