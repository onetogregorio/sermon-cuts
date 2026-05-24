# Use cases — three concrete workflows

**English** · [Português](USE_CASES.pt.md) · [Español](USE_CASES.es.md)

The pipeline is the same for everything, but the rhythm changes by
context. Pick the workflow closest to what you're doing, follow the
checklist, adapt freely.

---

## 1. Sunday sermon (most common)

You preached today. You want 5–10 vertical clips up on Reels and
TikTok by Tuesday morning. ~45 minutes of total work.

**Prep (10 min):**
- Upload your sermon to YouTube (unlisted is fine — auto-captions get
  generated either way after ~30 min).
- Confirm your sermon audio is clearly audible (re-mic if scratchy).
- Note any segments you want skipped (announcements at the start,
  altar call at the end).

**Run (5 min wallclock + ~1 min compute):**
```bash
./scripts/pipeline.sh "https://youtube.com/watch?v=YOUR_VIDEO"
```
This ingests + transcribes + finds pause boundaries. Output: a ranked
list of ~10 proposed cuts.

**Curate (10–15 min):**
- Skim the proposed list (ranked by `coherence_score`).
- For each candidate, read the hook + conclusion in
  `cuts_proposed.json`.
- Approve the 5–8 strongest.
- Reject anything where the hook needs context you can't see.

**Render approved cuts (~5–10 min):**
```bash
./scripts/pipeline.sh --render-cuts 1,3,5,7,9 --slug <your-sermon>
```
Cuts land in `renders/<your-sermon>/`. Each is vertical 1080×1920,
captioned, audio-leveled, ready to upload.

**Review (10 min):**
- Open each MP4 in QuickTime/VLC (not macOS Preview — see TROUBLESHOOTING).
- For each: watch start + end, listen for clipping, confirm
  captions match.
- Reject anything that doesn't land.

**Publish (5 min):**
- Move approved ones to `edit/cuts/<Sermon Name>/`.
- Upload to your scheduler (Postiz, Hootsuite, native uploaders).
- Caption each with the hook from `cuts_proposed.json` + your CTA.

**Total real time:** ~45 min on a quiet Monday. Most weeks you'll
trust the pipeline more and shave 15 min off curation.

---

## 2. Series of 4 sermons (release plan)

You preached a 4-part Sunday series. You want to release content from
the series across 8 weeks (~3 cuts per week, themed roll-out).

**Prep — once:**
- Decide the release schedule. Example:
  - Week 1: hook clip from sermon 1 + 2 supporting clips
  - Week 2: deeper clip from sermon 1 + bridge to sermon 2
  - …etc.
- Pick a slug naming convention. Example: `serie_efesios_01`,
  `serie_efesios_02`, …
- Create a tracking spreadsheet: `cut_slug | release_date | platform |
  caption | hashtags | plays_7d`.

**Run — per sermon:**
```bash
for n in 01 02 03 04; do
  ./scripts/pipeline.sh "https://youtube.com/watch?v=URL_${n}" \
    --slug serie_efesios_${n}
done
```

**Curate — once, all together:**
- After all 4 sermons are transcribed, open all 4
  `cuts_proposed.json` files side by side.
- Pick 8 strongest cuts total across the series (not 8 per sermon —
  the goal is the SERIES arc).
- Map each cut to its release date.

**Render selected:**
```bash
./scripts/pipeline.sh --render-cuts 1,3,5 --slug serie_efesios_01
./scripts/pipeline.sh --render-cuts 2,6 --slug serie_efesios_02
# …etc
```

**Theme rotation tip:** keep a `memory/hashtags/<theme>.txt` file for
each recurring theme (fé, propósito, oração, mente renovada, …) with
8–12 hashtags per theme. Rotate the packs across cuts so your account
doesn't get flagged for hashtag spam.

---

## 3. Multi-day conference (multiple speakers)

You hosted or recorded a conference: 6 speakers, 2 days, 12 sessions
total. You want a content drip for 2–3 months that pulls people back
to register for next year.

**Prep:**
- Separate each speaker's session into its own video file (don't mix
  speakers in one MP4 — face tracking will go crazy).
- Get each speaker's permission in writing before publishing their cuts.
- Pick a slug per session: `conf2025_doe_jane_keynote`,
  `conf2025_smith_john_panel`, etc. Long slugs are OK — folder
  organization wins over brevity here.

**Per session:**
```bash
./scripts/pipeline.sh ~/conf2025/raw/<speaker>_<session>.mp4 \
  --slug conf2025_<speaker>_<session>
```
Note: passing a local MP4 (not a YouTube URL) skips the
transcription via YouTube and uses Groq automatically — make sure
`GROQ_API_KEY` is set.

**Curate — pick the 5 strongest cuts per session.** Don't release all
of them — quality over quantity for conference content. Target 30
total cuts for the 2-month drip (~5 per session × 6 sessions).

**Brand consistency:** if you have an event brand (logo, color), set
up a custom style preset in `config/style_presets/conf2025.txt` and
point `config/render_defaults.yaml` at it for the duration. Reverts
back to your default for personal content.

**Speaker attribution:** add an opening title card to each cut credit-
ing the speaker (their name + IG handle + which session). This goes
beyond what the pipeline does — drop the MP4 in CapCut/DaVinci for
that single overlay. Keeps speakers happy and makes them more likely
to share.

---

## Cross-cutting tips

### Improving cut quality

- **Better source audio = better cuts.** A clipped or noisy source
  hurts both transcription accuracy and final-video listenability.
  Re-mic if you can.
- **Brief the LLM.** If your tradition or style differs from a
  Brazilian Christian sermon, edit `prompts/propose_cuts.md` to
  describe what makes a great cut for YOUR audience.
- **Use a per-sermon `corrections.txt`** for theological terms or
  proper nouns your transcriber consistently misses. See
  [PRIVACY.md](PRIVACY.md) and [FAQ.md](FAQ.md).

### Backing up your work

`memory/messages/<slug>/` and `edit/cuts/` are gitignored on purpose
(they're large + sometimes private). But you DON'T want to lose them.
Pick one:
- rsync to external drive (manual, low effort): `rsync -av memory/
  /Volumes/Backup/sermon-cuts-memory/`
- iCloud Drive symlink (sync, automatic)
- Private GitHub repo paralelo with its own LFS

### Tracking what works

A simple spreadsheet with columns `cut_slug | platform | release_date |
plays_7d | saves | shares` will teach you within 4 weeks which
patterns retain in your audience. Adjust your cut-proposal rubric in
`prompts/propose_cuts.md` based on what you learn.

---

By [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
