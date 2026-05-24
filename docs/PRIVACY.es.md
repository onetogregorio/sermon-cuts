# Privacidad & manejo de datos

[English](PRIVACY.md) · [Português](PRIVACY.pt.md) · **Español**

Sermon Cuts es un pipeline local-first. El flujo predeterminado
mantiene tu video y audio del sermón completamente en tu computadora.
Este documento es la respuesta honesta a *"si ejecuto esto, ¿quién ve
qué?"*.

---

## TL;DR para pastores

- **Tu archivo de video nunca sale de tu computadora** bajo ningún proveedor.
- **Tu audio sale de tu computadora SOLO** si eliges `--provider=groq`
  para transcripción.
- **El texto de la transcripción** se envía a tu editor de IA (Claude,
  Cursor, etc.) cuando le pides que proponga cortes — igual que
  cualquier prompt que pegarías manualmente.
- **El MP4 final renderizado** queda local hasta que tú mismo lo subas.

Para privacidad máxima: usa `--provider=youtube` para transcripción y
**no** pases `--use-llm` al scrub de SRT. Todo lo demás es local.

---

## Qué datos toca cada paso del pipeline

### `01_ingest.py` — obteniendo el video fuente

| Fuente que le das | Qué sale de tu máquina |
|---|---|
| URL de YouTube | URL es consultada por `yt-dlp` para descargar el video. Tráfico YouTube estándar. |
| Archivo `.mp4` local | Nada. Archivo es symlinkeado o copiado a `memory/messages/<slug>/source.mp4`. |

### `02_transcribe.py` — palabras con marcas de tiempo

| `--provider=` | Qué sale de tu máquina |
|---|---|
| `youtube` (predeterminado) | La URL de YouTube es consultada vía `yt-dlp` para descargar el archivo VTT de auto-subtítulos. **No se sube audio.** Los subtítulos se parsean localmente. |
| `groq` | El audio completo del sermón se extrae a un WAV temporal y se sube a la API Groq Whisper-large-v3 para transcribir. Ver la [política de privacidad de Groq](https://groq.com/privacy-policy/). |

### `03_vad_segments.py` — encontrar pausas naturales

100% local. Ejecuta [silero-vad](https://github.com/snakers4/silero-vad)
sobre el audio in-process. **Ningún dato sale de tu máquina.**

### `04_propose_cuts.py` — pedirle cortes a la IA

Este script en sí NO llama ninguna API — solo prepara la transcripción
y datos del VAD para que tu editor de IA los lea.

Cuando tú (o tu editor) actúa sobre el prompt:
- **El texto de la transcripción + marcas de tiempo de candidatos VAD**
  se envían al proveedor de tu editor de IA (Anthropic, OpenAI, etc.)
  como parte del prompt.
- **No se envía audio.**
- El archivo de video no se envía — solo la representación de texto.

Si tu editor de IA te permite elegir modelo (ej. claude-haiku vs
claude-opus), puedes usar un modelo más pequeño para ahorrar; el texto
transcrito compartido es el mismo.

### `05_validate_cut.py` — verificando límites limpios del corte

100% local. Lee transcript + VAD + cuts JSON, escribe de vuelta al disco.

### `06_build_srt.py` — generando el archivo de subtítulo

100% local. Sin acceso a internet.

### `06b_scrub_srt.py` — lint del SRT buscando errores de transcripción

| Modo | Qué sale de tu máquina |
|---|---|
| Predeterminado (solo rule-based) | Nada. Patrones regex corren localmente. |
| `--use-llm` | El texto del SRT + un prompt corto se envían o a Anthropic (si `ANTHROPIC_API_KEY` está set) o a Groq (si `GROQ_API_KEY` está set). |
| `--agent-review` | Nada automáticamente. Escribe un prompt estructurado para tu editor de IA interactivo leer. |

### `07_render_track.py` — face tracking y quemar subtítulos

100% local. MediaPipe corre in-process. En la primera ejecución,
descarga el modelo BlazeFace (~10 MB) de
`storage.googleapis.com/mediapipe-models/` — después de eso, sin
acceso a internet.

### `08_audio_normalize.py` — nivelar audio a -14 LUFS

100% local. Filtro `loudnorm` de ffmpeg hace todo.

### `09_trim_silences.py` — remoción opcional de silencio muerto

100% local.

---

## La receta de privacidad máxima

Si quieres **cero datos saliendo de tu máquina** más allá de la URL de
YouTube en sí, ejecuta:

```bash
# Transcribe localmente (o vía VTT de YouTube — que es solo consulta de URL)
./scripts/02_transcribe.py <slug> --provider=youtube

# Ejecuta la propuesta de cortes tú mismo, leyendo la transcripción
# manualmente en lugar de vía Claude/Cursor — o usa un LLM local
# (ollama, llama.cpp)

# Omite --use-llm en scrub
./scripts/06b_scrub_srt.py <slug> <n>     # sin flag --use-llm

# Renders son locales por diseño
./scripts/07_render_track.py <slug> <n>
./scripts/08_audio_normalize.py <slug> <n>
```

Si tu fuente es un `.mp4` local (no YouTube), la consulta de URL también
desaparece — **fully air-gapped** de principio a fin.

---

## Qué se almacena en tu máquina

El pipeline escribe todo en dos directorios en tu computadora:

```
sources/<slug>/source.mp4          # o symlink a tu original
memory/messages/<slug>/
├── transcript.json                # marcas de tiempo a nivel de palabra
├── vad.json                       # segmentos de pausa/habla
├── cuts_proposed.json             # propuestas de corte de la IA
├── corrections.txt                # tus correcciones de SRT por-sermón
├── srts/NN-slug.srt              # archivos de subtítulo quemados
└── (no se almacena archivo de audio por separado)

renders/<slug>/
└── NN-slug.mp4                    # clips verticales finales
```

Todo esto queda en tu máquina. El pipeline nunca sube nada de esto a un
servidor remoto. Si quieres backup, eres responsable de él (ver el
ritual de CLAUDE.md para un enfoque: rsync a disco externo o iCloud).

---

## Lo que NO se recolecta

El pipeline contiene **cero telemetría**. Sin analytics, sin reporte de
errores, sin stats de uso. No llama a casa. Las únicas llamadas de red
son las listadas en este documento, todas disparadas por flags de línea
de comandos que tú elegiste explícitamente.

---

## Notas específicas por proveedor

### Groq Whisper

Cuando optas vía `--provider=groq`:
- El chunk completo de audio se sube.
- Según la [política de Groq](https://groq.com/privacy-policy/), retienen
  inputs por un periodo corto para monitoreo de abuso; no (al momento de
  esto) usan inputs de API para entrenar modelos.
- Si manejas conversaciones pastorales sensibles (consejería,
  grabaciones de oración), considera si la conveniencia vale la pena.

### Anthropic / OpenAI (vía tu editor de IA)

Cuando usas Claude Code, Cursor, etc.:
- Ya estás regido por sus términos de privacidad existentes.
- El texto de la transcripción se envía — sin audio.
- Sus políticas de retención y entrenamiento aplican.

### YouTube (yt-dlp)

Cuando pasas una URL de YouTube:
- La URL es consultada.
- Para `--provider=youtube`, solo el archivo de auto-subtítulos se descarga.
- Para `--provider=groq`, el video se descarga localmente (para poder
  ser re-encodado a audio).
- Ningún dato personal tuyo se envía a YouTube más allá de lo que tu
  IP ya revela.

---

## Preguntas

Abre una issue en [GitHub](https://github.com/onetogregorio/sermon-cuts/issues)
o contacto vía [netogregorio.com](https://netogregorio.com).

---

Escrito por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
