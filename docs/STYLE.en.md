# Style guide — sermon-cuts

[**English**](STYLE.en.md) · [Português](STYLE.md) · [Español](STYLE.es.md)

Opinionated visual defaults the `sermon-cuts` skill applies on every render. Read this before proposing any change to subtitle, animation, or layout. For purely local overrides (font path, alternate palette for a different brand), use the consuming project's `CLAUDE.md`.

## Brand palette

| Token | Hex | RGB | Use |
|---|---|---|---|
| `navy-deep` | `#192a56` | `(25, 42, 86)` | Accent — background blocks, animation fills. **Not** for subtitle outline. |
| `gold-warm` | `#fbc531` | `(251, 197, 49)` | Subtitle text, accent highlights |
| `pure-black` | `#000000` | `(0, 0, 0)` | Subtitle outline — clean, sharp contrast |

ASS subtitle color encoding (Aegisub/libass uses `&HAABBGGRR`):
- `gold-warm` `PrimaryColour` = `&H0031C5FB`
- `pure-black` `OutlineColour` = `&H00000000`

## Typography

- **Family:** Outfit
- **Default weight:** 800 (Black)
- **ASS FontName:** `Outfit` (libass picks the Black variant when `Bold=1`)
- Fallback if Outfit is missing: Helvetica Bold

The skill assumes `Outfit` is available on the system (libass resolves it by name). If you need to point to a specific `.ttf` on your disk, override `font_path` in `config/render_defaults.yaml` or in `memory/messages/<slug>/overrides.yaml`.

## Subtitle rules

- **Never UPPERCASE.** Use sentence case or natural case. Capitalize only the first word and proper nouns.
- Chunking: 3–5 words per line (not 2 — it gets too choppy for Outfit Black, which is already heavy).
- Text: `gold-warm` `#fbc531`
- Outline: **black** `#000000`, **`Outline=0.8`** (~5px at 1920-high frame) — thin, elegant, hugs the letters without weighing them down. Navy looks bad as an outline — keep it for blocks/animation only.
- No shadow, no background fill — let the outline carry contrast.
- `MarginV`: **50** — subtitle at the footer. Above the Instagram/TikTok/Reels UI bar (which occupies ~150–180px at the bottom of a 1920 frame), but positioned as a classic footer, not floating in the middle of the chest.
- Alignment: 2 (bottom center)

## Reusable `force_style` string

```
FontName=Outfit,FontSize=16,Bold=1,
PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,
BorderStyle=1,Outline=0.8,Shadow=0,
Alignment=2,MarginV=50
```

**Actual size at vertical 1080×1920** (libass scales based on PlayResY=288):
- `FontSize=16` → ~107 px text height (~5.5% of screen height)
- `Outline=0.8` → ~5 px thin black outline
- `MarginV=50` → subtitle at footer, above Insta/TikTok UI

Default chunking for this size: **3–4 words per line, max ~20 chars** (Outfit Black is wide, breaks easily).

The full string also lives in `config/force_style.txt` for direct consumption by `render.py`. Per-message override in `memory/messages/<slug>/overrides.yaml`.

## Animation palette (when needed)

Same two colors:
- Background or fill: `navy-deep` `#192a56`
- Highlights, accents, text: `gold-warm` `#fbc531`
- Use Outfit Black for any kinetic typography overlay.

Avoid introducing extra accent colors without confirming.

## Format default

**Vertical 1080×1920 @ 30fps. Always. Hard rule.** Doesn't matter if the source is horizontal (16:9 from YouTube/stage) or vertical from an iPhone — the final output is **always** full 1080×1920.

**How to convert horizontal source to vertical:**

Use **scale + crop** (fills the frame, crops the sides). NEVER scale + pad with blurred background, NEVER horizontal letterbox in the middle with black bars top/bottom — looks ugly and amateur.

ffmpeg recipe for 1920×1080 source → 1080×1920:
```
-vf "scale=-2:1920,crop=1080:1920"
```

This scales preserving aspect up to height 1920 (width becomes ~3413), then crops the central 1080 of width. The speaker is big, centered, fills the screen.

If the point of interest isn't horizontally centered in the source, adjust crop X manually (`crop=1080:1920:X:0`). But the default is center — and `07_render_track.py` handles this automatically via MediaPipe face tracking.

**What NOT to do:**
- ❌ Small horizontal video in the middle of the vertical frame with blurred background top/bottom
- ❌ Letterbox with black bars
- ❌ Horizontal source rendered as horizontal and then rotated/boxed

## File organization (cuts)

Each **message/sermon/content** gets its own subfolder inside `edit/cuts/`. Final files sit directly in the subfolder, named with the pattern `NN-slug.mp4`:

```
edit/cuts/
├── Destroying strongholds/         ← message name (human-readable, may contain spaces)
│   ├── 01-stronghold_and_protection.mp4
│   ├── 02-no_thought_is_neutral.mp4
│   └── ...
└── <Other message>/
    ├── 01-theme.mp4
    └── ...
```

Naming rules:
- `NN-` prefix with leading zero (01, 02 … 10) — keeps alphabetical order = cut order
- `snake_case` slug, ASCII, describing the beat (`stronghold_and_protection`, `forgiveness_in_retail`)
- No `cut_`, `_VERTICAL`, `_LEGENDADO` or any pipeline suffix — the final file is what matters
- `.mp4` extension

Intermediates (EDLs, SRTs, verify frames, render preview) live in `edit/edls/`, `edit/srts/`, `edit/verify/` etc. — outside `cuts/`. The per-message subfolder in `cuts/` is reserved for the finals that ship.

---

By [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
