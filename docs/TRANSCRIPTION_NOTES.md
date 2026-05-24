# Transcription notes

**English** · [Português](TRANSCRIPTION_NOTES.pt.md) · [Español](TRANSCRIPTION_NOTES.es.md)

## YouTube auto-captions vs Groq Whisper

| | YouTube VTT | Groq Whisper-large-v3 |
|---|---|---|
| **Cost** | Free | Free tier covers most use; paid if heavy |
| **Speed** | ~3 sec (just download VTT) | ~30 sec per 10 min audio |
| **Quality** | Good but rare-word errors | State-of-art accuracy |
| **Needs API key** | No | Yes (`GROQ_API_KEY`) |
| **Works offline** | No | No |
| **Languages** | Many (auto-detect or `--language`) | 99 languages |
| **Word-level timestamps** | Yes (inline `<HH:MM:SS.mmm>` tags) | Yes (`timestamp_granularities=["word"]`) |

### Common YouTube auto-caption errors we've seen (PT-BR)

These often need a quick manual fix after `06_build_srt.py`:

- **Truncated joined sentences**: when one sentence ends and another
  starts in the same audio span, YouTube can drop a word.
  Example: `superestimamos a missão. Mas a missão...` → `superestimamos a Mas`
- **Mid-sentence word drops**: similar issue; YouTube favors compact
  output and sometimes loses a connector.
  Example: `vem para uma relação, então...` → `vem para uma Então`
- **Sermon-specific terms**: theological vocabulary occasionally
  mis-transcribed (e.g. "Cristo" → "Quisto" in noisy audio).

For high-stakes content (paid sponsor reads, public release), prefer
`--provider=groq`. For high-volume daily content (10+ cuts/day from
sermons), YouTube VTT + manual corrections is faster overall.

## Schema reference

Both providers emit the same JSON shape:

```json
{
  "words": [
    {"text": "Eu",       "start": 1.95, "end": 2.12, "type": "word"},
    {"text": " ",        "start": 2.12, "end": 2.13, "type": "spacing"},
    {"text": "gosto",    "start": 2.13, "end": 2.48, "type": "word"},
    {"text": " ",        "start": 2.48, "end": 2.50, "type": "spacing"},
    {"text": "de",       "start": 2.50, "end": 2.62, "type": "word"},
    ...
  ],
  "language": "pt",
  "_provider": "youtube-vtt"
}
```

`type: "spacing"` entries are synthetic — they represent the gap between
two consecutive words and are useful for downstream code that needs to
distinguish breath/pause boundaries from contiguous speech.

## Adding a new provider

To add e.g. Deepgram or AssemblyAI:

1. Add an entry to the `--provider` choices in `02_transcribe.py`
2. Implement `transcribe_<name>()` returning `{words, language, _provider}`
3. Use `_to_scribe_shape()` to normalize raw words → the shape above

The downstream pipeline (VAD, propose, SRT, render) doesn't care which
provider produced the transcript.

## Correcting transcript errors in the loop

After `06_build_srt.py` you can:

1. Inspect `memory/messages/<slug>/srts/NN-slug.srt`
2. Identify suspicious cues (often: short cue with weird capitalization
   mid-sentence, or a sentence ending without a period)
3. Fix the cue text directly — the timestamps stay valid
4. Re-burn only: `./scripts/pipeline.sh --reburn-srt N --slug <slug>`
   (this skips re-tracking, saves ~30s per cut)

For high-volume work, consider an LLM-assisted correction step:
have Claude scan the SRT for likely transcription errors and propose
fixes — much faster than reviewing each cue by hand.
