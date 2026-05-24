# Walkthrough del pipeline

[English](PIPELINE.md) · [Português](PIPELINE.pt.md) · **Español**

Cada script escribe en `memory/messages/<slug>/` y es idempotente (re-ejecutar
es seguro y omite el trabajo hecho a menos que use `--force`).

## 01_ingest.py

```bash
./scripts/01_ingest.py <youtube-url-o-ruta-local> [--slug SLUG]
```

URL de YouTube → usa yt-dlp para descargar la mejor calidad hasta 1080p como MP4.
Archivo local → enlaces simbólicos (o copia si falla el symlink).

Escribe:
- `memory/messages/<slug>/source.mp4`
- `memory/messages/<slug>/meta.json` (URL/ruta/título/duración)

Derivación del slug: desde el título del YouTube o nombre del archivo (convertido a snake_case).
Sobrescriba con `--slug`.

## 02_transcribe.py

```bash
./scripts/02_transcribe.py <slug> [--provider=youtube|groq] [--language=pt]
```

### YouTube (predeterminado, gratis, instantáneo)

Llama a `yt-dlp --write-auto-subs --skip-download` para obtener el archivo VTT de subtítulos automáticos
que YouTube genera para cada video público. Analiza marcas de tiempo a nivel de palabra
del VTT (esas etiquetas `<HH:MM:SS.mmm>` entre palabras).

### Groq (pagado-ish, mayor calidad)

Extrae audio (WAV mono 16kHz), sube a Groq Whisper-large-v3 con
`timestamp_granularities=["word"]`. Devuelve marcas de tiempo a nivel de palabra.
Necesita `GROQ_API_KEY` en env.

Salida (mismo formato para ambos):

```json
{
  "words": [
    {"text": "Eu", "start": 1.95, "end": 2.12, "type": "word"},
    {"text": " ", "start": 2.12, "end": 2.13, "type": "spacing"},
    ...
  ],
  "language": "pt",
  "_provider": "youtube-vtt"  // o "groq-whisper-large-v3"
}
```

## 03_vad_segments.py

```bash
./scripts/03_vad_segments.py <slug> [--min-silence 0.5]
```

Ejecuta [silero-vad](https://github.com/snakers4/silero-vad) en el audio
fuente (remuestreado a 16kHz mono). Detecta segmentos de habla → deriva
los silencios entre ellos → marca el punto medio de cada silencio ≥ 0.5s como
**punto de corte candidato** (lugares donde un corte no dividirá palabra/respiración).

Salida:

```json
{
  "speech": [{"start": 0.34, "end": 12.18}, ...],
  "silences": [{"start": 12.18, "end": 13.05, "duration": 0.87}, ...],
  "candidate_cut_points": [12.18, 28.71, ...]
}
```

## 04_propose_cuts.py

```bash
./scripts/04_propose_cuts.py <slug>
```

Empaqueta transcripción + VAD en un único `propose_input.json` y imprime
las rutas que el LLM (Claude) debe leer, más el prompt en
`prompts/propose_cuts.md`. **Este script no llama a un LLM** — solo
prepara entradas.

Se espera que el LLM escriba los cortes propuestos en
`memory/messages/<slug>/cuts_proposed.json`.

Esquema esperado para cada corte:

```json
{
  "n": 1,
  "slug": "filha_no_mercado",
  "start": 92.40,
  "end": 165.10,
  "duration_s": 72.7,
  "theme": "Relación vs misión — ilustración de la hija en el mercado",
  "hook": "Eu gosto de uma ilustração muito boa...",
  "development": "...",
  "conclusion": "Jesus pede que a gente vá COM ele, não pra ficar n'Ele",
  "coherence_score": 9.2,
  "tags": ["ilustracao", "relacionamento_com_deus"],
  "vad_aligned": true
}
```

Vea `prompts/propose_cuts.md` para la rúbrica completa.

## 05_validate_cut.py

```bash
./scripts/05_validate_cut.py <slug> <cut_index> [--write-back] [--max-extend-s 8]
```

Confirma que la última palabra del corte no es un final prohibido (configurable en
`config/render_defaults.yaml` — ej. "porque", "mas", "que", "para", "com",
"de"). Si lo es, intenta extender el final hasta el siguiente punto de corte candidato del VAD
dentro de `max-extend-s` segundos donde la palabra ya no esté prohibida.

`--write-back` aplica el parche al corte en `cuts_proposed.json`.

## 06_build_srt.py

```bash
./scripts/06_build_srt.py <slug> <cut_index>
```

Genera un SRT brand-styled desde las palabras de la transcripción en el rango del corte:

- 3-4 palabras por subtítulo, máx ~20 caracteres (configurable)
- Divide en la puntuación (`. ! ?` hard, `, ; :` soft si el subtítulo tiene ≥3 palabras)
- Divide en pausa ≥0.5s si el subtítulo tiene ≥3 palabras
- Desplazamiento consciente de palabra-función: si un subtítulo termina con "para"/"com"/"que"/etc.,
  desplaza al siguiente subtítulo (así los subtítulos nunca terminan en palabra-función)
- Capitaliza el primer subtítulo
- Quita la puntuación suave final del texto del subtítulo

Escribe `memory/messages/<slug>/srts/NN-slug.srt`.

## 07_render_track.py

```bash
./scripts/07_render_track.py <slug> <cut_index> [--no-subs]
```

Renderizado de dos pases:

**Pase 1 — muestreo de posición facial.** A 2 fps (predeterminado), ejecuta el detector
MediaPipe BlazeFace short-range en el frame del fuente. Registra el center-X
de la cara más grande detectada. Respaldo a Haar cascade de OpenCV si
falla MediaPipe.

**Suavizado.** Media móvil de 2.5s (5 muestras) de las posiciones X de la cara
elimina el jitter de detección y da una sensación cinemática.

**Pase 2 — renderiza frame por frame.** Por cada frame del fuente:
1. Escala a altura 1920 preservando aspecto (1920×1080 → 3413×1920)
2. Interpola X suavizado para la marca de tiempo del frame actual
3. Recorta 1080×1920 centrado en esa X (clamped a los límites del frame)
4. Pipe de raw BGR frames a ffmpeg para codificación H.264 (CRF 18 preset slow)

**Mux de audio.** Combina video codificado con el segmento de audio del fuente.

**Burn de subtítulos.** Aplica el filtro ffmpeg `subtitles=` con `force_style`
de `config/force_style.txt`. Omita con `--no-subs`.

Escribe `memory/messages/<slug>/renders/NN-slug.mp4`.

## 08_audio_normalize.py

```bash
./scripts/08_audio_normalize.py <slug> <cut_index> [--target-lufs -14] [--in-place]
```

Mide loudness integrado con pyloudnorm (ITU-R BS.1770-4), aplica
ganancia para alcanzar el LUFS objetivo. Re-codifica audio a AAC 192k, copia stream de video.

`--in-place` sobrescribe el render original. De lo contrario escribe un
hermano `.normalized.mp4`.

## pipeline.sh

Orquestador:

```bash
# Ingest + transcribe + VAD + prepare propose-input
./scripts/pipeline.sh "https://youtube.com/watch?v=XXX"

# Renderiza índices específicos end-to-end (validate + SRT + render + normalize)
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug mi_sermon

# Solo re-burn de subtítulos (después de corregir transcripción) sin re-tracking
./scripts/pipeline.sh --reburn-srt 3 --slug mi_sermon
```

## Layout de directorio por mensaje

Después de una ejecución completa:

```
memory/messages/<slug>/
├── source.mp4              # symlink o descarga
├── meta.json               # URL/título/duración
├── transcript.json         # nivel de palabra con type=word/spacing
├── vad.json                # segmentos de habla + candidatos de corte
├── propose_input.json      # entrada combinada para el LLM
├── cuts_proposed.json      # salida del LLM (usted cura esto)
├── srts/
│   └── NN-slug.srt
└── renders/
    └── NN-slug.mp4         # final, listo para subir
```

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
