# Changelog

## 0.1.0 — Initial release (2026-05-23)

First public release. End-to-end pipeline:

- `01_ingest.py` — yt-dlp or local file → managed source
- `02_transcribe.py` — YouTube VTT (default) or Groq Whisper, word-level
- `03_vad_segments.py` — silero-vad pause detection → cut candidates
- `04_propose_cuts.py` — prepares LLM input for cut proposal
- `05_validate_cut.py` — auto-extends cuts that end mid-thought
- `06_build_srt.py` — brand-style subtitles (3-4 words, function-word shift)
- `07_render_track.py` — MediaPipe face tracking + smooth pan + burn subs
- `08_audio_normalize.py` — pyloudnorm to -14 LUFS
- `pipeline.sh` — orchestrator

Default brand style: Outfit Black, gold `#fbc531`, black `0.8` outline,
sentence case, footer position. Vertical 1080×1920 @ 30fps.

Includes a `SKILL.md` for Claude Code integration.

Tested with two PT-BR sermons (~28min each):
- *Vinde a mim* (Mateus 11) — 12 cut candidates proposed, 8 rendered.
- *Derrubando as fortalezas da mente* — 10 cuts rendered.

Sample case studies in `examples/`.
