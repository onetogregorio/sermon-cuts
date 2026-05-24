---
name: sermon-cuts
description: "End-to-end pipeline for cutting vertical short-form clips from long sermon/preaching videos. Triggered when the user wants to cut a sermon, preaching, pregação, mensagem, or sermon-style talking-head video into multiple short verticals (Reels/Shorts/TikTok). Handles: download (YouTube or local), Groq Whisper transcription, VAD-aware natural cut boundaries, LLM-proposed cuts with narrative-arc scoring, MediaPipe face-tracking smooth pan, brand-style burned subtitles (gold Outfit Black + black outline + footer), LUFS audio normalization. User curates which proposed cuts to render; the rest is automatic."
---

# sermon-cuts — pipeline for sermon cuts

[**English**](SKILL.en.md) · [Português](SKILL.md) · [Español](SKILL.es.md)

## When to invoke

You invoke this skill when the user asks things like:
- "let's cut this sermon https://..."
- "cut this message into N 1-minute cuts"
- "make cuts from the sermon"
- "transcribe and cut this preaching for Reels/Shorts"
- "find the best beats of this message"

Accepts as input a **YouTube URL** OR a local `.mp4`/`.mov` path.

## Final output

In `<project>/edit/cuts/<message_slug>/`:
```
01-cut_theme.mp4
02-another_beat.mp4
...
```

Each cut is:
- **Vertical 1080×1920 @ 30fps** (scale + crop with smooth face tracking)
- **Burned-in subtitle** brand-style (Outfit Black, gold `#fbc531`, black outline 0.8, footer MarginV=50, 3-4 words/line, sentence case)
- **Normalized audio** to -14 LUFS (Insta/TikTok/Reels standard)
- **H.264 CRF 18 preset slow** (high quality, reasonable file size)

## Workflow (one-at-a-time mode — Neto prefers this)

### Phase A — Ingest + analysis (automatic, ~1 min)

1. **`scripts/01_ingest.py <url-or-path>`** — downloads via yt-dlp (1080p or better) OR copies local to `memory/messages/<slug>/source.mp4`
2. **`scripts/02_transcribe.py`** — Groq Whisper-large word-level → `transcript.json`
3. **`scripts/03_vad_segments.py`** — silero-vad detects pauses ≥0.8s → `vad.json` (candidate boundaries)

### Phase B — Cut proposal (LLM, ~30s)

4. **You (Claude) read** `transcript.json` + `vad.json` and propose cuts following `prompts/propose_cuts.md`. Output: `cuts_proposed.json` with `[{n, slug, start, end, theme, hook, conclusion, coherence_score, depends_on}]`
5. **Present to the user** as a list ranked by score. They pick which to approve.

### Phase C — Render per approved cut (~30-60s each)

For each approved cut:
6. **`scripts/05_validate_cut.py`** — confirms natural ending (no truncated "porque nós"). If invalid, adjusts by extending to next valid VAD pause.
7. **`scripts/06_build_srt.py`** — generates brand-style SRT from the segment
8. **`scripts/07_render_track.py`** — MediaPipe face detection (2 fps) + smoothing (2.5s moving avg) + dynamic 1080×1920 crop → vertical without subtitle
9. **Burn subtitle** (ffmpeg + subtitles filter + force_style)
10. **`scripts/08_audio_normalize.py`** — pyloudnorm -14 LUFS on final audio
11. **Save** to `<project>/edit/cuts/<slug>/NN-cut_slug.mp4` and show preview to Neto

### Phase D — Iteration

If he rejects/asks for change in a cut:
- Subtitle text correction → edit `srt`, reburn (no re-tracking)
- Trim start/end → re-run from step 7
- Whole cut wrong → mark rejected in `cuts_proposed.json`, propose replacement

## File structure

```
~/.claude/skills/sermon-cuts/
├── SKILL.md                 ← this file
├── scripts/
│   ├── 01_ingest.py
│   ├── 02_transcribe.py
│   ├── 03_vad_segments.py
│   ├── 04_propose_cuts.py   ← stub that calls Claude with prompt
│   ├── 05_validate_cut.py
│   ├── 06_build_srt.py
│   ├── 07_render_track.py
│   ├── 08_audio_normalize.py
│   └── pipeline.sh          ← end-to-end orchestrator
├── config/
│   ├── force_style.txt
│   ├── function_words_pt.txt
│   └── render_defaults.yaml
├── prompts/
│   └── propose_cuts.md
└── memory/
    └── messages/
        └── <message_slug>/
            ├── source.mp4
            ├── transcript.json
            ├── vad.json
            ├── cuts_proposed.json
            └── status.json     ← per-cut: proposed/approved/rendered/rejected
```

## Hard rules (don't negotiate with user)

1. **Vertical 1080×1920**. Horizontal source → `scale=-2:1920,crop=1080:1920` with dynamic X tracking via MediaPipe. **Never** letterbox, **never** scale+pad with blur background.
2. **Subtitle sentence case**, never UPPERCASE.
3. **Black outline 0.8**, FontSize 16, MarginV 50. Don't invent.
4. **Cut must have complete arc**: hook → development → conclusion. If LLM can't identify a clear conclusion, reject the cut.

## Decisions that should be deferred to the user (don't automate)

- Which cuts to approve (final curation)
- Transcription correction when Whisper misses a technical/theological word
- Override of cut theme/slug

## Typical invocation commands

```bash
# Full pipeline, interactive mode (default)
~/.claude/skills/sermon-cuts/scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# Just ingest + transcribe + propose (no render)
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --propose-only /path/local.mp4

# Render specific cuts already proposed
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --render-cuts 2,4,7 --slug vinde_a_mim

# Re-apply only subtitle (no retracking) on an already done cut
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --reburn-srt 2 --slug vinde_a_mim
```

## Brand style

Palette, typography, subtitle rules, format default, and file organization live in **[docs/STYLE.en.md](docs/STYLE.en.md)** — read it before proposing any visual change. TL;DR: gold `#fbc531` + black outline, Outfit Black, vertical 1080×1920, sentence case.

Purely local overrides (custom font path, alternate palette for a different brand) belong in the consuming project's `CLAUDE.md`, not here.

---

By [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
