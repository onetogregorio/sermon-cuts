# Subtitle style presets

Each `.txt` here is a libass [`force_style`](https://aegisub.org/docs/latest/ass_tags/)
string applied during the burn-in pass of `07_render_track.py`. Select one
in `config/render_defaults.yaml`:

```yaml
subtitle:
  preset: arial-black     # default — universal, ships on every OS
  # preset: helvetica-bold  # macOS-native alternative
  # preset: outfit-black    # warm display font; install Outfit first
```

## Available presets

| Preset | Font | Availability | Notes |
|---|---|---|---|
| `arial-black` | Arial Black | macOS · Windows · most Linux (Liberation Sans fallback) | **Default.** Bold, neutral, reads well at 1080p. |
| `helvetica-bold` | Helvetica Bold | macOS native; Linux fallback to DejaVu | Cleaner than Arial Black, slightly less weight. |
| `outfit-black` | Outfit Black | Requires manual install ([Google Fonts](https://fonts.google.com/specimen/Outfit)) | Warm display font. The default brand style used on the project landing. |

## Picking your own

Drop a new `.txt` here (e.g. `mybrand.txt`) following the same single-line
format, then set `subtitle.preset: mybrand` in `render_defaults.yaml`.
The `force_style` syntax is documented in the
[libass ASS tags reference](https://aegisub.org/docs/latest/ass_tags/).

Key fields you'll likely change:

- `FontName=` — anything libass can resolve via fontconfig (`fc-list`)
- `PrimaryColour=&H00BBGGRR` — text fill, ASS encoding (BB GG RR, not RGB!)
- `OutlineColour=&H00BBGGRR` — outline color
- `FontSize=` — at 1080×1920 with default PlayRes, `16` ≈ 107px tall
- `Outline=` — outline thickness in ASS units (0.8 ≈ 5px at 1080)
- `MarginV=` — distance from bottom edge in ASS units (50 lands above
  the Reels/TikTok UI bar)

## Advanced override

Backward compat: if `config/force_style.txt` exists, it takes priority
over `subtitle.preset`. Removing it (or setting it to a symlink pointing
at one of the presets) brings you back to preset selection.
