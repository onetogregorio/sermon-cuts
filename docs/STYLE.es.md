# Guía de estilo — sermon-cuts

[English](STYLE.en.md) · [Português](STYLE.md) · [**Español**](STYLE.es.md)

Defaults visuales con opinión que el skill `sermon-cuts` aplica en cada render. Léelo antes de proponer cualquier cambio de subtítulo, animación o layout. Para overrides puramente locales (ruta de fuente, paleta alternativa de otra marca), usa el `CLAUDE.md` del proyecto consumidor.

## Paleta de marca

| Token | Hex | RGB | Uso |
|---|---|---|---|
| `navy-deep` | `#192a56` | `(25, 42, 86)` | Accent — bloques de fondo, rellenos de animación. **No** usar como outline de subtítulo. |
| `gold-warm` | `#fbc531` | `(251, 197, 49)` | Texto de subtítulo, highlights |
| `pure-black` | `#000000` | `(0, 0, 0)` | Outline de subtítulo — contraste limpio y nítido |

Codificación de color ASS (Aegisub/libass usa `&HAABBGGRR`):
- `gold-warm` `PrimaryColour` = `&H0031C5FB`
- `pure-black` `OutlineColour` = `&H00000000`

## Tipografía

- **Familia:** Outfit
- **Peso default:** 800 (Black)
- **ASS FontName:** `Outfit` (libass elige la variante Black cuando `Bold=1`)
- Fallback si Outfit no está instalada: Helvetica Bold

El skill asume que `Outfit` está disponible en el sistema (libass la resuelve por nombre). Si necesitas apuntar a un `.ttf` específico en tu disco, sobreescribe `font_path` en `config/render_defaults.yaml` o en `memory/messages/<slug>/overrides.yaml`.

## Reglas de subtítulo

- **Nunca MAYÚSCULAS.** Usa sentence case o caja natural. Capitaliza solo la primera palabra y nombres propios.
- Chunking: 3–5 palabras por línea (no 2 — queda muy picado para Outfit Black, que ya es pesada).
- Texto: `gold-warm` `#fbc531`
- Outline: **negro** `#000000`, **`Outline=0.8`** (~5px en frame 1920) — fino, elegante, acompaña las letras sin pesar. Navy queda feo como outline — usar solo para bloques/animación.
- Sin shadow, sin background fill — deja que el outline cargue el contraste.
- `MarginV`: **50** — subtítulo en el pie. Arriba de la barra de UI de Instagram/TikTok/Reels (que ocupa ~150–180px del fondo en un frame 1920), pero posicionado como pie clásico, no en medio del pecho.
- Alignment: 2 (centro inferior)

## String `force_style` reutilizable

```
FontName=Outfit,FontSize=16,Bold=1,
PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,
BorderStyle=1,Outline=0.8,Shadow=0,
Alignment=2,MarginV=50
```

**Tamaño real en frame vertical 1080×1920** (libass escala con base en PlayResY=288):
- `FontSize=16` → ~107 px de altura de texto (~5.5% de la altura de pantalla)
- `Outline=0.8` → ~5 px de outline negro fino
- `MarginV=50` → subtítulo en el pie, arriba de la UI de Insta/TikTok

Chunking default para este tamaño: **3–4 palabras por línea, máx ~20 chars** (Outfit Black es ancha, rompe fácil).

La string completa también vive en `config/force_style.txt` para consumo directo por `render.py`. Override por mensaje en `memory/messages/<slug>/overrides.yaml`.

## Paleta de animación (cuando se necesite)

Los mismos dos colores:
- Fondo o fill: `navy-deep` `#192a56`
- Highlights, accents, texto: `gold-warm` `#fbc531`
- Usa Outfit Black para cualquier overlay de typography cinética.

Evita introducir colores accent extra sin confirmar.

## Format default

**Vertical 1080×1920 @ 30fps. Siempre. Hard rule.** No importa si la fuente es horizontal (16:9 de YouTube/escenario) o vertical de iPhone — el output final es **siempre** 1080×1920 completo.

**Cómo convertir source horizontal a vertical:**

Usa **scale + crop** (llena el frame, corta los lados). NUNCA scale + pad con fondo difuminado, NUNCA letterbox horizontal en medio con barras negras arriba/abajo — queda feo y amateur.

Receta ffmpeg para source 1920×1080 → 1080×1920:
```
-vf "scale=-2:1920,crop=1080:1920"
```

Esto escala manteniendo aspect hasta altura 1920 (ancho queda ~3413), después corta el centro 1080 de ancho. El speaker queda grande, centrado, llena la pantalla.

Si el punto de interés no está en el centro horizontal del source, ajusta el crop X manualmente (`crop=1080:1920:X:0`). Pero el default es centro — y `07_render_track.py` lo resuelve automáticamente vía MediaPipe face tracking.

**Lo que NO hacer:**
- ❌ Video horizontal pequeño en medio del frame vertical con fondo difuminado arriba/abajo
- ❌ Letterbox con barras negras
- ❌ Source horizontal renderizado como horizontal y después rotado/encajado

## Organización de archivos (cuts)

Cada **mensaje/sermón/contenido** tiene su propia subcarpeta dentro de `edit/cuts/`. Los archivos finales van directo en la subcarpeta, nombrados con el patrón `NN-slug.mp4`:

```
edit/cuts/
├── Destruyendo fortalezas/         ← nombre del mensaje (legible, puede tener espacios)
│   ├── 01-fortaleza_y_proteccion.mp4
│   ├── 02-ningun_pensamiento_es_neutro.mp4
│   └── ...
└── <Otro mensaje>/
    ├── 01-tema.mp4
    └── ...
```

Reglas de nombre:
- Prefijo `NN-` con cero a la izquierda (01, 02 … 10) — mantiene orden alfabético = orden de corte
- Slug en `snake_case`, ASCII, describiendo el beat (`fortaleza_y_proteccion`, `perdon_al_por_menor`)
- Sin `cut_`, `_VERTICAL`, `_LEGENDADO` o cualquier sufijo de pipeline — el archivo final es lo que importa
- Extensión `.mp4`

Intermediarios (EDLs, SRTs, frames de verify, render preview) viven en `edit/edls/`, `edit/srts/`, `edit/verify/` etc. — fuera de `cuts/`. La subcarpeta por mensaje en `cuts/` se reserva para los finales que se publican.

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
