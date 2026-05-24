# sources/

Source videos land here, one folder per sermon (slug):

```
sources/
├── README.md           ← this file
├── vinde/
│   └── source.mp4      ← created by 01_ingest.py
├── destruindo_fortalezas/
│   └── source.mp4
└── …
```

## How the source.mp4 gets here

You don't put it here by hand — `01_ingest.py` does. From a YouTube URL:

```bash
./scripts/pipeline.sh "https://youtube.com/watch?v=…"
```

`yt-dlp` downloads the best ≤1080p version, merges audio+video to mp4,
and writes it to `sources/<slug-derived-from-title>/source.mp4`.

From a local file:

```bash
./scripts/01_ingest.py /path/to/your/sermon.mp4 --slug my_message
```

A **symlink** to your original file is created at
`sources/my_message/source.mp4` — your original isn't copied or moved,
so you can keep it wherever you already store sermons.

## What about extras?

Each `<slug>/` is yours to add to:

- `notes.md` — your own notes / curation thoughts
- `alt-angle.mp4` — second-camera angle, if relevant later
- `outline.pdf` — sermon outline

Nothing in `sources/` is committed to git (the `.gitignore` blocks
`*.mp4` and friends), so personal files stay personal.

## Where output goes

→ Renders land in [`../renders/<slug>/`](../renders/) — see the README there.
→ Pipeline state (transcripts, SRTs, VAD) lives in the hidden
   `~/.claude/skills/sermon-cuts/memory/messages/<slug>/`. You usually
   never need to touch that folder.

## Overriding the location

Set the env var `SERMON_CUTS_SOURCES_DIR` to put sources somewhere else
(e.g. an external drive). Same path is then used by all pipeline scripts.
