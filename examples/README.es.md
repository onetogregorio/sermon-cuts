# Ejemplos

[English](README.md) · [Português](README.pt.md) · **Español**

Esta carpeta muestra lo que produce el pipeline, usando dos sermones reales en PT-BR
procesados durante el desarrollo.

## `sample_cuts/`

Un único ejemplo de salida (comprimido para tamaño del repo):

- `01-fortaleza_e_protecao_demo.mp4` (5.3 MB, 37s)
  Corte #1 de *"Derrubando as fortalezas da mente"*. Vertical 1080×1920,
  subtítulos brand (Outfit Black oro + outline negro + posición de pie de página),
  seguimiento facial, audio normalizado. Esa es la salida cruda del pipeline,
  lista para subir a Reels/Shorts/TikTok.

> El repo solo incluye una demo para mantenerse ligero. En uso real el pipeline
> produce 8-12 cortes de ese tipo por sermón de ~30min.

## Case studies

### `case_destruindo_fortalezas.md`

Análisis en markdown de los 10 cortes propuestos para el sermón
*"Derrubando as fortalezas da mente"*, con el tema de cada corte, la
estructura hook/desarrollo/conclusión, y las marcas de tiempo del source original.
Eso es como se ve un `cuts_proposed.json` como doc human-readable.

### `case_destruindo_fortalezas_takes.md`

Notas tras bastidores del paso de curación — qué cortes mantener, cuáles
fusionar, cuáles rechazar y por qué.

## Transcripciones de ejemplo

### `vinde_transcript_sample.json` (~470 KB)

Transcripción a nivel de palabra de *"Vinde a mim"* (Mateo 11), sermón de 27:44, en
el schema producido por `02_transcribe.py`. 4016 palabras. Use esto para
inspeccionar el formato o para testear scripts downstream sin re-ejecutar
transcripción.

### `destruindo_fortalezas_transcript_sample.json`

Mismo shape, sermón diferente. ~38min.

## `srts_destruindo_fortalezas/`

Los 10 archivos SRT producidos por `06_build_srt.py` para los cortes de *Destruindo
fortalezas*. Muestra el brand-style chunking (3-4 palabras, function-word
shift, sentence case) en acción.

---

## Cómo reproducir la demo

1. Ponga un video largo de sermón PT-BR en `sources/su_sermon.mp4`
2. `./scripts/pipeline.sh sources/su_sermon.mp4`
3. (Lea la transcripción + proponga cortes manualmente O pídaselo al Claude)
4. `./scripts/pipeline.sh --render-cuts 1,2,3 --slug su_sermon`

Los cortes caen en `memory/messages/su_sermon/renders/`.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
