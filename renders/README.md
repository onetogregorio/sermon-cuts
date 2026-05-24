# renders/

The final vertical cuts ready to publish, one folder per sermon (slug):

```
renders/
├── README.md           ← this file
├── vinde/
│   ├── 01-filha_no_mercado.mp4
│   ├── 02-alma_cansada.mp4
│   ├── 03-internet_e_instalo.mp4
│   └── …
├── destruindo_fortalezas/
│   ├── 01-fortaleza_e_protecao.mp4
│   └── …
└── …
```

## What's in each MP4

Every cut here is:

- **1080×1920 @ 30 fps** — vertical, ready for Reels / Shorts / TikTok
- **Face-tracked** — speaker centered horizontally with smooth pan
- **Subtitled** — burned-in brand-style captions (your active preset:
  see `config/render_defaults.yaml` → `subtitle.preset`)
- **Audio normalized to -14 LUFS** — Instagram/TikTok loudness standard
- Optionally silence-trimmed (when `cuts_proposed.json` has
  `trim_silences: true` on that cut)

## How the files got here

`pipeline.sh --render-cuts N,M,P --slug <slug>` runs the chain:

1. `05_validate_cut` — confirms each cut ends naturally
2. `06_build_srt` — generates brand-style subtitle file
3. `06b_scrub_srt` — lints the SRT (you can review suspects before burn)
4. **`07_render_track`** — face-tracked vertical render with burned subs
   → writes to `renders/<slug>/NN-slug.mp4`
5. `08_audio_normalize` — loudness pass (overwrites in place)
6. `09_trim_silences` — opt-in silence compression (overwrites in place)

## Publishing workflow

Pick up the MP4s here, upload directly to Reels / Shorts / TikTok / X.
The filenames are stable (`NN-slug.mp4`) so you can drag them into a
scheduling tool in order.

Once published, you don't need to keep the file here — it's regenerable
from the source + cuts_proposed.json. But there's no harm in keeping it
either; nothing in `renders/` is committed to git.

## Overriding the location

Set `SERMON_CUTS_RENDERS_DIR` to write renders somewhere else (an
external drive, a synced Dropbox/iCloud folder, etc.). All pipeline
scripts pick up the new path.
