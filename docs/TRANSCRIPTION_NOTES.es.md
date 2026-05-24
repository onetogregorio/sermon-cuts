# Notas de transcripción

[English](TRANSCRIPTION_NOTES.md) · [Português](TRANSCRIPTION_NOTES.pt.md) · **Español**

## Subtítulos automáticos YouTube vs Groq Whisper

| | YouTube VTT | Groq Whisper-large-v3 |
|---|---|---|
| **Costo** | Gratis | Tier gratuito cubre la mayoría; pagado si es pesado |
| **Velocidad** | ~3 seg (solo descargar VTT) | ~30 seg por 10 min de audio |
| **Calidad** | Buena pero errores en palabras raras | Precisión state-of-the-art |
| **Necesita clave API** | No | Sí (`GROQ_API_KEY`) |
| **Funciona offline** | No | No |
| **Idiomas** | Muchos (auto-detect o `--language`) | 99 idiomas |
| **Marcas de tiempo a nivel de palabra** | Sí (etiquetas inline `<HH:MM:SS.mmm>`) | Sí (`timestamp_granularities=["word"]`) |

### Errores comunes de subtítulos automáticos de YouTube que hemos visto (PT-BR)

Estos a menudo necesitan una corrección manual rápida después de `06_build_srt.py`:

- **Frases pegadas truncadas**: cuando una frase termina y otra
  comienza en el mismo span de audio, YouTube puede soltar una palabra.
  Ejemplo: `superestimamos a missão. Mas a missão...` → `superestimamos a Mas`
- **Drops de palabra en medio de la frase**: problema similar; YouTube favorece output
  compacto y a veces pierde un conector.
  Ejemplo: `vem para uma relação, então...` → `vem para uma Então`
- **Términos específicos de sermón**: vocabulario teológico ocasionalmente
  mal-transcrito (ej. "Cristo" → "Quisto" en audio con ruido).

Para contenido high-stakes (lecturas pagas de patrocinador, lanzamiento público), prefiera
`--provider=groq`. Para contenido diario high-volume (10+ cortes/día de
sermones), YouTube VTT + correcciones manuales es más rápido en general.

## Schema de referencia

Ambos providers emiten el mismo formato JSON:

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

Entradas `type: "spacing"` son sintéticas — representan el gap entre
dos palabras consecutivas y son útiles para código downstream que necesita
distinguir límites de respiración/pausa de habla contigua.

## Agregar un nuevo provider

Para agregar ej. Deepgram o AssemblyAI:

1. Agregue una entrada a las opciones `--provider` en `02_transcribe.py`
2. Implemente `transcribe_<nombre>()` devolviendo `{words, language, _provider}`
3. Use `_to_scribe_shape()` para normalizar raw words → el shape de arriba

El pipeline downstream (VAD, propose, SRT, render) no le importa cuál
provider produjo la transcripción.

## Corrigiendo errores de transcripción en el loop

Después de `06_build_srt.py` puede:

1. Inspeccionar `memory/messages/<slug>/srts/NN-slug.srt`
2. Identificar subtítulos sospechosos (a menudo: subtítulo corto con capitalización extraña
   en medio de la frase, o frase terminando sin punto)
3. Corregir el texto del subtítulo directamente — las marcas de tiempo siguen válidas
4. Re-burn solamente: `./scripts/pipeline.sh --reburn-srt N --slug <slug>`
   (esto omite el re-tracking, ahorra ~30s por corte)

Para trabajo high-volume, considere un paso de corrección asistido por LLM:
pida al Claude que escanee el SRT en busca de errores probables de transcripción y proponga
correcciones — mucho más rápido que revisar cada subtítulo a mano.

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
