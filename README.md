# Sermon Cuts

**English** · [Português](README.pt.md) · [Español](README.es.md)

> **Skill for Claude, Cursor, and other AI coding agents** that turns long
> preaching, sermon, or talk videos into ready-to-publish vertical clips for
> Reels, Shorts, and TikTok — already cropped, captioned, and audio-balanced.
> Paste a YouTube link. Pick your favorite moments. Get the cuts.

---

## What you get

You drop in a 30-, 40-, even 60-minute message — your sermon, your conference
talk, your livestream — and walk away with a folder of **vertical shorts ready
to upload**. Each one:

- Reframed vertically (1080×1920) with the speaker centered, smoothly
- Subtitled in your brand style — gold text, clean outline, no shouting caps
- Balanced to platform-standard loudness so it sounds right on Instagram and TikTok
- Named, numbered, and organized so you know what to post and when

What used to be a full Sunday-night editing session in CapCut becomes
**~5 minutes of curation**. You decide what to publish. The pipeline does the rest.

---

## Built for creators of the Word

Most short-form content tools are built for marketers selling shoes. This one
is built for **pastors, preachers, evangelists, teachers, content creators
talking about faith** — people whose message deserves better than a rushed
afternoon in Premiere.

It already knows:

- That a great cut needs a **hook**, a **development**, and a **conclusion** —
  not just a 60-second slice of someone talking
- That cuts can't end on "porque…" or "mas…" — they have to land
- That the subtitle font matters, that the audio level matters, that the
  centering of the speaker's face on a vertical frame matters
- That **you** are the one who picks the final cuts — the AI proposes, you decide

Made with portuguese-language sermons in mind, but works in any language
(`--language=en`, `pt`, `es`, etc).

---

## Use it as a skill in your AI editor

This whole pipeline is wrapped as a [Claude Code](https://claude.com/claude-code)
skill — meaning you can just say to your AI assistant:

> *"cut this sermon: https://youtube.com/watch?v=…"*
> *"corta essa pregação"*
> *"make 8 vertical clips of this message for Instagram"*

…and the agent handles transcription, cut proposals, face tracking, subtitles,
audio normalization, and rendering. You only step in for the part that matters:
**choosing which moments of your message are worth publishing**.

Works the same way with **Cursor**, **Cline**, **Aider**, or any IDE/agent that
can read a `SKILL.md` and run shell scripts.

---

## Install with one prompt 🪄

Don't want to read install docs? Paste this prompt into **Claude Code**,
**Cursor**, **Codex**, **Cline**, **Aider** — any AI coding agent with shell
access — and it'll install the whole thing for you.

> Install the **Sermon Cuts** skill (https://github.com/onetogregorio/sermon-cuts)
> on this machine. Walk me through these steps and stop if anything fails:
>
> 1. Detect my OS (macOS or Linux). On macOS, make sure Homebrew is installed.
> 2. Install system deps: `ffmpeg` (with libass), `yt-dlp`, Python 3.12+.
> 3. Clone the repo to `~/code/sermon-cuts` (or ask me where).
> 4. Create a Python venv inside the repo and `pip install -r requirements.txt`.
> 5. Symlink `scripts/`, `config/`, `prompts/` into `~/.claude/skills/sermon-cuts/`
>    and copy `SKILL.md` there too.
> 6. Ask if I want to enable better transcription via Groq Whisper. If yes,
>    open https://console.groq.com/keys, ask me to paste the key, and add
>    `GROQ_API_KEY=...` to `~/.env`.
> 7. Ask if I want the brand font Outfit Black (https://fonts.google.com/specimen/Outfit).
>    If yes, download it and install to my user fonts folder.
> 8. Run `./scripts/pipeline.sh --help` to confirm the skill is wired up.
> 9. Tell me a one-line example of how to cut my first sermon.
>
> Report success or the failed step at the end.

That's it. Next, just say *"cut this sermon: <YouTube URL>"* to the same agent.

---

## Quick start (manual)

If you'd rather run it yourself:

```bash
# 1. Ingest + transcribe + find natural cut boundaries  (~1 min for a 30min sermon)
./scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# 2. Claude (or you) reads the transcript and proposes ~10 cuts.
#    A ranked list shows up; you pick which ones to render.

# 3. Render the cuts you approved  (~30–60s per cut on Apple Silicon)
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug my_sermon
```

Final cuts land in:

```
memory/messages/<slug>/renders/01-cut_slug.mp4
memory/messages/<slug>/renders/02-cut_slug.mp4
...
```

Vertical 1080×1920, branded subtitles burned in, audio at -14 LUFS — ready to
upload to Reels, Shorts, or TikTok. See [`examples/sample_cuts/`](examples/sample_cuts/)
for a real output.

> First-time setup: see [INSTALL.md](docs/INSTALL.md) — you need `ffmpeg`,
> Python deps, and a one-time symlink so the skill scripts resolve from
> `~/.claude/skills/sermon-cuts/`.

---

## What's inside

Each step is a standalone script — combine them however you like, or just run
`pipeline.sh` end-to-end.

| Script | What it does |
|---|---|
| `01_ingest.py` | YouTube URL or local video → managed source file |
| `02_transcribe.py` | Word-level transcription (free via YouTube, or premium via Groq Whisper) |
| `03_vad_segments.py` | Finds natural pauses so cuts never split mid-word |
| `04_propose_cuts.py` | Packages the message for the AI to propose narrative-arc cuts |
| `05_validate_cut.py` | Auto-fixes cuts that end mid-thought |
| `06_build_srt.py` | Brand-style subtitles: 3-4 words, gold, sentence case |
| `07_render_track.py` | Face-tracking vertical reframe + burned subtitle |
| `08_audio_normalize.py` | Audio balanced to -14 LUFS (the Reels/TikTok standard) |
| `pipeline.sh` | One command to run it all |

Full walkthrough in [`docs/PIPELINE.md`](docs/PIPELINE.md).
Install in [`docs/INSTALL.md`](docs/INSTALL.md).

---

## Install

```bash
# macOS
brew install ffmpeg yt-dlp python@3.12
pip install -r requirements.txt
```

(Linux instructions and optional Groq API setup in [`docs/INSTALL.md`](docs/INSTALL.md).)

---

## Make it look like yours

Edit two files and the whole pipeline adopts your brand:

- `config/force_style.txt` — subtitle font, color, position
- `config/render_defaults.yaml` — resolution, frame rate, audio target

Default style is built for the gold-on-black look used in the
[netogregorio.com](https://netogregorio.com) content — but it's all yours
to change.

---

## See it in action

Check [`examples/`](examples/) for two full case studies — the cuts proposed,
the curation decisions made, and the final vertical outputs ready to publish.

Or visit the [project landing page](https://onetogregorio.github.io/sermon-cuts/) →

---

## Sponsors

Built with support from organizations investing in tools that serve the church
and faith content creators.

<!-- SPONSORS:START -->
- **[Midvash](https://midvash.com)** — Online Bible with AI · 9 languages,
  70 Bible versions, semantic search and study tools powered by language models.
- **MinhaIgreja** — _TODO: URL + short description_
<!-- SPONSORS:END -->

Want to support this project? [Become a sponsor →](https://github.com/sponsors/onetogregorio)

---

## About me

Hi, I'm **Neto Gregório** — I build tools at the intersection of faith,
creativity, and AI. I made Sermon Cuts because I was tired of spending Sunday
night cutting my own messages into Reels by hand, and I figured other people
preaching, teaching, and creating spiritual content might be tired of it too.

If this project saves you an evening, I'd love to hear about it.

→ **Blog**: [netogregorio.com](https://netogregorio.com) — essays on faith,
  technology, and building with AI agents
→ **Instagram**: [@onetogregorio](https://instagram.com/onetogregorio) — behind
  the scenes, sermon clips, daily thoughts
→ **GitHub**: [@onetogregorio](https://github.com/onetogregorio)

Built with [Claude Code](https://claude.com/claude-code).

---

## License

MIT — see [`LICENSE`](LICENSE). Use it freely. Cut more messages. Reach more people.
