# Examples

This folder shows what the pipeline produces, using two real PT-BR sermons
processed during development.

## `sample_cuts/`

A single example output (compressed for repo size):

- `01-fortaleza_e_protecao_demo.mp4` (5.3 MB, 37s)
  Cut #1 from *"Derrubando as fortalezas da mente"*. Vertical 1080×1920,
  branded subtitles (Outfit Black gold + black outline + footer position),
  face tracking, normalized audio. This is the raw output of the pipeline,
  ready to upload to Reels/Shorts/TikTok.

> The repo only includes one demo to stay light. In actual use the pipeline
> produces 8-12 such cuts per ~30min sermon.

## Case studies

### `case_destruindo_fortalezas.md`

Markdown analysis of all 10 cuts proposed for the sermon
*"Derrubando as fortalezas da mente"*, with the theme of each cut, the
hook/development/conclusion structure, and the original source timestamps.
This is what a `cuts_proposed.json` looks like as a human-readable doc.

### `case_destruindo_fortalezas_takes.md`

Behind-the-scenes notes from the curation pass — which cuts to keep, which
to merge, which to reject and why.

## Sample transcripts

### `vinde_transcript_sample.json` (~470 KB)

Word-level transcript of *"Vinde a mim"* (Mateus 11), 27:44 sermon, in
the schema produced by `02_transcribe.py`. 4016 words. Use this to
inspect the format or to test downstream scripts without re-running
transcription.

### `destruindo_fortalezas_transcript_sample.json`

Same shape, different sermon. ~38min.

## `srts_destruindo_fortalezas/`

The 10 SRT files produced by `06_build_srt.py` for the *Destruindo
fortalezas* cuts. Shows the brand-style chunking (3-4 words, function-word
shift, sentence case) in action.

---

## How to reproduce the demo

1. Drop a long PT-BR sermon video at `sources/your_sermon.mp4`
2. `./scripts/pipeline.sh sources/your_sermon.mp4`
3. (Read transcript + propose cuts manually OR ask Claude to)
4. `./scripts/pipeline.sh --render-cuts 1,2,3 --slug your_sermon`

Cuts land at `memory/messages/your_sermon/renders/`.
