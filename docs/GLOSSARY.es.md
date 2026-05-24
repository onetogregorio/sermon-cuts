# Glosario

[English](GLOSSARY.md) · [Português](GLOSSARY.pt.md) · **Español**

Definiciones en lenguaje directo de los términos que verás en los docs,
prompts y mensajes de error. Léelo una vez y el resto del proyecto
queda más fácil de entender.

---

## Anatomía del pipeline

**Pipeline** — la cadena de scripts (`01_ingest` → `02_transcribe` →
… → `08_audio_normalize`) que transforma un sermón largo en clips
verticales cortos. Cada script hace una cosa y escribe a disco antes
de pasar al siguiente.

**Skill** — el wrapper que permite a agentes de IA (Claude Code,
Cursor, Cline, Aider, etc.) invocar el pipeline conversacionalmente.
Es solo un `SKILL.md` + la carpeta `scripts/`. Cuando dices "corta
esta predicación" en Claude Code, lee el `SKILL.md` y ejecuta los
comandos correctos.

**Slug** — nombre corto, computer-friendly, de un sermón (sin
espacios, sin acentos). Ejemplos: `vinde`, `derrubando_fortalezas`,
`mateo_11_domingo`. Cada sermón obtiene su propio slug y su propio
directorio de trabajo.

**Directorio de trabajo** — `memory/messages/<slug>/`. Donde vive
todo sobre un sermón: transcripción, propuestas de cortes, SRTs,
correcciones.

---

## Anatomía del corte

**Cut (corte)** — un clip corto producido del sermón. Un sermón de 30
min típicamente rinde 8-12 cortes de 25-60 segundos cada uno.

**Hook (gancho)** — la frase de apertura del corte. Los primeros 1-2
segundos que o atrapan al viewer o lo pierden. Hook fuerte es
concreto, específico, sorprendente.

**Desarrollo** — lo que pasa en el medio. La historia se desenvuelve,
el punto se construye, la analogía se explora.

**Conclusión / payoff** — la frase final. Donde el corte aterriza.
Debe resolver lo que el hook prometió — punchline, aplicación, cita
bíblica.

**Coherence score** — rating de 0-10 que el LLM asigna a cada corte
propuesto basado en cuán bien hook + desarrollo + conclusión encajan
como una idea self-contained.

---

## Subtítulos

**SRT** — `.srt` (SubRip Text) es el formato estándar de subtítulo.
Texto plano con números de cue, marcas de tiempo y texto. Sermon Cuts
escribe un SRT por corte.

**Cue** — una entrada en un SRT. Típicamente 3-4 palabras mostradas
juntas en pantalla por 0,5-2 segundos.

**Palabra-función** — palabras cortas como "de", "para", "con",
"que", "pero", "porque" que conectan ideas pero no llevan sentido
solas. Las cues nunca deben terminar en ellas — el ojo se queda
esperando la siguiente palabra. El chunker tiene lógica para
shiftarlas hacia adelante.

**Forbidden ending** — palabra-función al final de una cue. El
pipeline intenta prevenirlo vía shift; lo que no se puede shiftar se
marca para revisión humana.

**Hook boost** — el markup ASS `{\fs22\b1}` auto-añadido a la
primera cue de cada corte. Hace la primera línea ligeramente más
grande + bold durante el burn-in para atraer la mirada en el scroll.

**Burn-in** — el acto de incrustar permanentemente subtítulos en los
píxeles del video (vs. enviar el SRT por separado). Una vez burned,
el subtítulo no se puede desactivar.

**libass** — la biblioteca que ffmpeg usa para renderizar
subtítulos ASS/SRT en video. Debe estar compilada en tu build de
ffmpeg para que el filtro `subtitles` funcione.

**`force_style`** — la string de estilización pasada a libass que
controla fuente, color, outline, tamaño, posición. Vive en
`config/style_presets/*.txt`.

---

## Audio

**LUFS** (Loudness Units Full Scale) — medida moderna de loudness
percibida. Instagram, TikTok, Reels y YouTube normalizan a ~-14 LUFS,
por eso ese es nuestro target.

**True peak (dBTP)** — nivel de pico real después de la reconstrucción
de audio. Diferente del sample peak. Targetamos -1.5 dBTP para tener
headroom y cero clipping.

**Clipping** — cuando el audio excede el nivel máximo representable y
queda cortado, produciendo un sonido distorsionado "crunchy". El
normalizer con true-peak limit lo previene.

**Loudnorm** — filtro de normalización de loudness EBU R128 de
ffmpeg. Estándar de la industria para broadcast y streaming.

---

## Tracking de video

**Face tracking** — muestrear posición de la cara frame por frame y
usarla para decidir dónde cortar el frame vertical. Mantiene al
predicador centrado incluso cuando camina por el escenario.

**MediaPipe** — toolkit ML open-source de Google. El pipeline usa el
detector de cara BlazeFace short-range y el pose landmarker (para
fallback en el hombro cuando face detection falla).

**VAD (Voice Activity Detection)** — algoritmo que identifica qué
partes del audio tienen habla vs. silencio. Sermon Cuts usa
[silero-vad](https://github.com/snakers4/silero-vad) para encontrar
pausas naturales donde los cortes pueden aterrizar sin dividir palabra.

**Pan smoothing** — promedio de las posiciones X de la cara sobre una
ventana de 2.5s para que el crop no tiemble mientras las detecciones
oscilan frame a frame. Le da al video final una sensación de pan
"cinematográfico".

**Ventana de crop** — la ventana de 1080 de ancho cortada del frame
fuente (típicamente 1920 de ancho) para producir el vertical 1080×1920
de salida.

---

## Tech de video

**BT.709** — el estándar de espacio de color para video HD. macOS
Preview se niega a mostrar videos H.264 limpiamente si su metadata
BT.709 no está explícitamente taggeada. El pipeline lo taggea en cada
render.

**H.264 / libx264** — el codec de video usado para la salida.
Estándar para web y plataformas sociales. CRF 18 (predeterminado) =
visualmente lossless.

**Preset (slow/fast/etc)** — tradeoff de velocidad vs. tamaño de
archivo del encode de libx264. `slow` = archivo más pequeño en la
misma calidad, tarda más. `fast` = archivo más grande, encoda más
rápido.

**MP4 / faststart** — formato contenedor. `+faststart` reordena el
archivo para que el playback pueda empezar antes del download
completo — esencial para streaming.

---

## Transcripción

**Whisper** — modelo speech-to-text open-source de OpenAI. Groq
hospeda una API de inferencia rápida para la variante large
(`whisper-large-v3`).

**Groq** — proveedor de inferencia third-party con API Whisper muy
rápida. El tier gratuito cubre la mayoría del uso personal.

**VTT** (Web Video Text Tracks) — formato de subtítulo de YouTube.
Sermon Cuts parsea los archivos VTT auto-generados de YouTube cuando
usas `--provider=youtube`.

**yt-dlp** — herramienta de línea de comandos open-source para
descargar videos y subtítulos de YouTube y muchas otras plataformas.

---

## Archivos & rutas

**`sources/<slug>/source.mp4`** — tu video crudo del sermón (o un
symlink a él).

**`memory/messages/<slug>/`** — artifacts de trabajo para un sermón
(transcript, VAD, propuestas de cortes, SRTs).

**`renders/<slug>/NN-slug.mp4`** — salida del pipeline. Vertical,
subtitulado, audio normalizado.

**`edit/cuts/<Nombre del Sermón>/`** — tu carpeta de curación para
los finales (según el ritual de CLAUDE.md; convención personal,
gitignored).

**`config/`** — defaults del pipeline, listas de palabras-función,
presets de estilo, diccionarios opcionales de corrección.

**`prompts/`** — system prompts enviados al LLM durante propuesta de
corte y scrub de SRT.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
