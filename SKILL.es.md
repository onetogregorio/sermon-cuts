---
name: sermon-cuts
description: "End-to-end pipeline for cutting vertical short-form clips from long sermon/preaching videos. Triggered when the user wants to cut a sermon, preaching, pregação, mensagem, or sermon-style talking-head video into multiple short verticals (Reels/Shorts/TikTok). Handles: download (YouTube or local), Groq Whisper transcription, VAD-aware natural cut boundaries, LLM-proposed cuts with narrative-arc scoring, MediaPipe face-tracking smooth pan, brand-style burned subtitles (gold Outfit Black + black outline + footer), LUFS audio normalization. User curates which proposed cuts to render; the rest is automatic."
---

# sermon-cuts — pipeline de cortes para predicaciones

[English](SKILL.en.md) · [Português](SKILL.md) · [**Español**](SKILL.es.md)

## Cuándo invocar

Invoca esta habilidad cuando el usuario pide cosas como:
- "vamos a cortar esa predicación https://..."
- "corta el mensaje en N cortes de 1 minuto"
- "hacer cortes del sermón"
- "transcribir y cortar esa predicación para Reels/Shorts"
- "encontrar los mejores beats de ese mensaje"

Acepta como input una **URL de YouTube** O una ruta local `.mp4`/`.mov`.

## Resultado final

En `<project>/edit/cuts/<slug_del_mensaje>/`:
```
01-tema_del_corte.mp4
02-otro_beat.mp4
...
```

Cada corte es:
- **Vertical 1080×1920 @ 30fps** (scale + crop con tracking suave de la cara)
- **Subtítulo burned-in** brand-style (Outfit Black, oro `#fbc531`, outline negro 0.8, pie de página MarginV=50, 3-4 palabras/línea, sentence case)
- **Audio normalizado** a -14 LUFS (estándar Insta/TikTok/Reels)
- **H.264 CRF 18 preset slow** (alta calidad, tamaño de archivo razonable)

## Workflow (modo one-at-a-time — Neto prefiere)

### Fase A — Ingest + análisis (automático, ~1 min)

1. **`scripts/01_ingest.py <url-o-ruta>`** — descarga vía yt-dlp (1080p o mejor) O copia local a `memory/messages/<slug>/source.mp4`
2. **`scripts/02_transcribe.py`** — Groq Whisper-large word-level → `transcript.json`
3. **`scripts/03_vad_segments.py`** — silero-vad detecta pausas ≥0.8s → `vad.json` (fronteras candidatas)

### Fase B — Propuesta de cortes (LLM, ~30s)

4. **Tú (Claude) lees** `transcript.json` + `vad.json` y propones cortes siguiendo `prompts/propose_cuts.md`. Output: `cuts_proposed.json` con `[{n, slug, start, end, theme, hook, conclusion, coherence_score, depends_on}]`
5. **Presenta al usuario** una lista ranqueada por score. Él elige cuáles aprobar.

### Fase C — Render por cut aprobado (~30-60s cada uno)

Para cada corte aprobado:
6. **`scripts/05_validate_cut.py`** — confirma final natural (sin "porque nós" truncado). Si es inválido, ajusta extendiendo hasta la siguiente pausa válida del VAD.
7. **`scripts/06_build_srt.py`** — genera SRT brand-style del segmento
8. **`scripts/07_render_track.py`** — MediaPipe face detection (2 fps) + smoothing (2.5s moving avg) + crop dinámico 1080×1920 → vertical sin subtítulo
9. **Burn subtítulo** (ffmpeg + subtitles filter + force_style)
10. **`scripts/08_audio_normalize.py`** — pyloudnorm -14 LUFS en el audio final
11. **Guarda** en `<project>/edit/cuts/<slug>/NN-cut_slug.mp4` y muestra preview a Neto

### Fase D — Iteración

Si él rechaza/pide cambio en un corte:
- Corrección de texto de subtítulo → edita `srt`, reburn (no rehace tracking)
- Trim de inicio/fin → re-correr desde paso 7
- Corte entero equivocado → marca rejected en `cuts_proposed.json`, propone sustituto

## Estructura de archivos

```
~/.claude/skills/sermon-cuts/
├── SKILL.md                 ← este archivo
├── scripts/
│   ├── 01_ingest.py
│   ├── 02_transcribe.py
│   ├── 03_vad_segments.py
│   ├── 04_propose_cuts.py   ← stub que llama Claude con prompt
│   ├── 05_validate_cut.py
│   ├── 06_build_srt.py
│   ├── 07_render_track.py
│   ├── 08_audio_normalize.py
│   └── pipeline.sh          ← orquestador end-to-end
├── config/
│   ├── force_style.txt
│   ├── function_words_pt.txt
│   └── render_defaults.yaml
├── prompts/
│   └── propose_cuts.md
└── memory/
    └── messages/
        └── <slug_mensaje>/
            ├── source.mp4
            ├── transcript.json
            ├── vad.json
            ├── cuts_proposed.json
            └── status.json     ← per-cut: proposed/approved/rendered/rejected
```

## Reglas hard (no negociar con usuario)

1. **Vertical 1080×1920**. Source horizontal → `scale=-2:1920,crop=1080:1920` con tracking dinámico de X vía MediaPipe. **Nunca** letterbox, **nunca** scale+pad con blur background.
2. **Subtítulo sentence case**, jamás UPPERCASE.
3. **Outline negro 0.8**, FontSize 16, MarginV 50. No inventar.
4. **Cut debe tener arco completo**: hook → desarrollo → conclusión. Si LLM no logra identificar conclusión clara, rechaza el cut.

## Decisiones que deben ser diferidas al usuario (no automatizar)

- Cuáles cortes aprobar (curación final)
- Corrección de transcripción cuando Whisper falla en palabra técnica/teológica
- Override de tema/slug del corte

## Comandos de invocación típicos

```bash
# Pipeline completo, modo interactivo (default)
~/.claude/skills/sermon-cuts/scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# Solo ingest + transcribe + propose (sin render)
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --propose-only /path/local.mp4

# Renderizar cortes específicos ya propuestos
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --render-cuts 2,4,7 --slug vinde_a_mim

# Reaplicar solo subtítulo (sin retracking) en un corte ya hecho
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --reburn-srt 2 --slug vinde_a_mim
```

## Brand style (referencia local — también en ~/.claude/projects/.../memory/video_brand_style.md)

```
Palette:
  gold-warm  #fbc531  — texto del subtítulo
  pure-black #000000  — outline
  navy-deep  #192a56  — accent solo (animaciones), nunca outline

Font: Outfit (Black, FontName=Outfit + Bold=1)

force_style:
  FontName=Outfit,FontSize=16,Bold=1,
  PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,
  BorderStyle=1,Outline=0.8,Shadow=0,
  Alignment=2,MarginV=50
```

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
