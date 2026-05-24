# Cortes de Sermón

[English](README.md) · [Português](README.pt.md) · **Español**

> **Skill para Claude, Cursor y otros agentes de IA** que transforma videos
> largos de predicación, sermón, conferencia o enseñanza en cortes verticales
> listos para publicar en Reels, Shorts y TikTok — ya encuadrados, subtitulados
> y con audio nivelado. Pega el link de YouTube. Elige tus momentos favoritos.
> Recibe los cortes.

---

## Lo que obtienes

Tiras un mensaje de 30, 40, hasta 60 minutos — tu predicación, tu conferencia,
tu live — y sales con una carpeta de **shorts verticales listos para subir**.
Cada uno:

- Reencuadrado vertical (1080×1920) con el predicador centrado, suave
- Subtitulado en tu estilo de marca — texto dorado, contorno limpio, sin MAYÚSCULAS
- Balanceado al loudness estándar de las plataformas para sonar bien en Insta y TikTok
- Numerado, nombrado y organizado para que sepas qué publicar y cuándo

Lo que era una noche entera de domingo en CapCut se convierte en
**~5 minutos de curación**. Tú decides qué publicas. El pipeline hace el resto.

---

## Hecho para quien predica la Palabra

La mayoría de las herramientas de cortes para short-form están hechas para
marketeros vendiendo zapatillas. Esta está hecha para **pastores, predicadores,
evangelistas, maestros, creadores de contenido cristiano** — gente cuyo mensaje
merece más que una tarde apurada en Premiere.

Ya sabe:

- Que un buen corte necesita un **hook**, un **desarrollo** y una **conclusión** —
  no solo una rebanada aleatoria de 60 segundos de alguien hablando
- Que un corte no puede terminar con "porque…" ni con "pero…" — tiene que aterrizar
- Que la fuente del subtítulo importa, que el nivel de audio importa, que el
  encuadre del rostro del predicador en el frame vertical importa
- Que **tú** eres quien elige los cortes finales — la IA propone, tú decides

Nació con sermones en portugués en mente, pero funciona en cualquier idioma
(`--language=en`, `pt`, `es`, etc).

---

## Úsalo como skill en tu editor de IA

El pipeline completo viene empaquetado como skill de
[Claude Code](https://claude.com/claude-code) — o sea, hablas con tu asistente
de IA tipo:

> *"corta esta predicación: https://youtube.com/watch?v=…"*
> *"haz 8 cortes verticales de este mensaje para Instagram"*
> *"separa los mejores momentos de este video para Reels"*

…y el agente se encarga de la transcripción, la propuesta de cortes, el
seguimiento facial, los subtítulos, la normalización de audio y el render.
Tú solo entras en la parte que importa: **elegir cuáles momentos de tu mensaje
merecen volverse contenido**.

Funciona igual con **Cursor**, **Cline**, **Aider** o cualquier IDE/agente que
lea un `SKILL.md` y ejecute scripts.

---

## Instala — elige tu camino

### 🟢 Lo más fácil: un comando en cualquier terminal

```bash
curl -fsSL https://onetogregorio.github.io/sermon-cuts/install.sh | bash
```

Detecta tu SO, instala ffmpeg/yt-dlp/Python, clona el repo, crea un venv,
hace symlinks del skill en `~/.claude/skills/sermon-cuts/`, opcionalmente
configura Groq + Outfit, y corre health check al final. **Se puede
re-ejecutar sin riesgo** — no sobrescribe nada existente.

### 🟡 A través de tu editor de IA (Claude Code, Cursor, Codex…)

Pega este prompt en cualquier editor con acceso al terminal:

> Instala el skill **Sermon Cuts** (https://github.com/onetogregorio/sermon-cuts)
> en mi máquina. Guíame por estos pasos y detente si alguno falla:
>
> 1. Detecta mi SO (macOS o Linux). En macOS, asegura Homebrew.
> 2. Instala deps del sistema: `ffmpeg` (con libass), `yt-dlp`, Python 3.12+.
> 3. Clona el repo en `~/code/sermon-cuts` (o pregúntame dónde).
> 4. Crea venv Python dentro del repo y ejecuta `pip install -r requirements.txt`.
> 5. Crea symlinks de `scripts/`, `config/`, `prompts/` hacia
>    `~/.claude/skills/sermon-cuts/` y copia `SKILL.md` allí.
> 6. Pregúntame si quiero transcripción mejor vía Groq Whisper. Si sí,
>    abre https://console.groq.com/keys, pídeme pegar la clave y agrega
>    `GROQ_API_KEY=...` en `~/.env`.
> 7. Pregúntame si quiero la fuente Outfit Black
>    (https://fonts.google.com/specimen/Outfit). Si sí, descárgala.
> 8. Ejecuta `./scripts/pipeline.sh doctor` para confirmar la instalación.
> 9. Dame un ejemplo de una línea de cómo cortar mi primer sermón.
>
> Reporta éxito o el paso que falló al final.

Después del install, solo dile *"corta esta predicación: \<URL de YouTube\>"* al mismo agente.

### 🐳 Docker (Linux/Windows/sin pip)

```bash
docker run --rm \
  -v "$(pwd)/out:/work/memory/messages" \
  -e GROQ_API_KEY=$GROQ_API_KEY \
  ghcr.io/onetogregorio/sermon-cuts <url-de-youtube>
```

> Build local: `docker build -t sermon-cuts .` si quieres ajustar la imagen.

---

## Workflow diario — los cuatro comandos que importan

```bash
pipeline.sh doctor                              # health check (corre esto primero)
pipeline.sh <url-o-mp4>                         # ingest + transcribe + propone cortes
pipeline.sh review <slug>                       # ↑↓ + SPACE + ENTER para elegir + render
pipeline.sh ui                                  # abre la UI web en localhost:7860
```

O, sin terminal alguno:

```bash
pipeline.sh ui                                  # drag-drop, checkboxes, descargas
```

> 💡 **¿Sin clave Groq?** Deja que `--provider=auto` elija `local`
> (usa faster-whisper offline, sin API key, ~1× tiempo real en Apple Silicon)
> o `youtube` (auto-captions, instantáneo, calidad ligeramente menor).

---

## Inicio rápido (manual)

Si prefieres ejecutarlo a mano:

```bash
# 1. Descarga + transcribe + encuentra las pausas naturales  (~1 min para un sermón de 30min)
./scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# 2. Claude (o tú) lee la transcripción y propone ~10 cortes.
#    Aparece una lista ranqueada; eliges cuáles renderizar.

# 3. Renderiza los cortes aprobados  (~30–60s por corte en Apple Silicon)
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug mi_predicacion
```

Los cortes finales aparecen en:

```
memory/messages/<slug>/renders/01-cut_slug.mp4
memory/messages/<slug>/renders/02-cut_slug.mp4
...
```

Vertical 1080×1920, subtítulo brand-style quemado, audio a -14 LUFS — listos
para subir a Reels, Shorts o TikTok. Vea [`examples/sample_cuts/`](examples/sample_cuts/)
para un output real.

> Setup inicial: ver [INSTALL.md](docs/INSTALL.es.md) — necesita `ffmpeg`,
> deps Python y un symlink único para que los scripts del skill resuelvan en
> `~/.claude/skills/sermon-cuts/`.

---

## Qué hay dentro

Cada paso es un script independiente — combínalos como quieras, o solo ejecuta
`pipeline.sh` end-to-end.

| Script | Qué hace |
|---|---|
| `01_ingest.py` | URL de YouTube o video local → archivo source administrado |
| `02_transcribe.py` | Transcripción a nivel de palabra (gratis vía YouTube, o premium vía Groq Whisper) |
| `03_vad_segments.py` | Encuentra pausas naturales para que los cortes nunca dividan palabras |
| `04_propose_cuts.py` | Empaqueta el mensaje para que la IA proponga cortes con arco narrativo |
| `05_validate_cut.py` | Arregla automáticamente cortes que terminan en medio del pensamiento |
| `06_build_srt.py` | Subtítulos brand-style: 3-4 palabras, dorado, sentence case |
| `07_render_track.py` | Reencuadre vertical con tracking facial + subtítulo quemado |
| `08_audio_normalize.py` | Audio nivelado a -14 LUFS (estándar Reels/TikTok) |
| `pipeline.sh` | Un comando para ejecutar todo |

Walkthrough completo en [`docs/PIPELINE.es.md`](docs/PIPELINE.es.md).
Instalación en [`docs/INSTALL.es.md`](docs/INSTALL.es.md).

---

## Instalación

```bash
# macOS
brew install ffmpeg yt-dlp python@3.12
pip install -r requirements.txt
```

(Instrucciones de Linux y setup opcional de la API Groq en [`docs/INSTALL.es.md`](docs/INSTALL.es.md).)

---

## Hazlo con tu cara

Edita dos archivos y todo el pipeline adopta tu marca:

- `config/force_style.txt` — fuente, color y posición del subtítulo
- `config/render_defaults.yaml` — resolución, frame rate, target de audio

El estilo predeterminado es el look dorado-en-negro usado en el contenido de
[netogregorio.com](https://netogregorio.com) — pero es todo tuyo para cambiar.

---

## Verlo funcionando

Revisa [`examples/`](examples/) para dos case studies completos — los cortes
propuestos, las decisiones de curación y los outputs verticales finales listos
para publicar.

O visita la [landing page del proyecto](https://onetogregorio.github.io/sermon-cuts/es/) →

---

## Patrocinadores

Construido con apoyo de organizaciones invirtiendo en herramientas que sirven
a la iglesia y a los creadores de contenido cristiano.

<!-- SPONSORS:START -->
- **[Midvash](https://midvash.com/es)** — Biblia online con IA · 9 idiomas,
  70 versiones de la Biblia, búsqueda semántica y herramientas de estudio impulsadas por modelos de lenguaje.
<!-- SPONSORS:END -->

¿Quieres apoyar este proyecto? [Vuélvete patrocinador →](https://github.com/sponsors/onetogregorio)

---

## Sobre mí

Hola, soy **Neto Gregório** — construyo herramientas en la intersección entre
fe, creatividad e IA. Hice Cortes de Sermón porque me cansé de pasar la noche
del domingo cortando mis propias predicaciones para Reels a mano, e imaginé
que más gente predicando, enseñando y creando contenido cristiano estaba
cansada también.

Si este proyecto te ahorra una noche, me encantaría saberlo.

→ **Blog**: [netogregorio.com](https://netogregorio.com) — ensayos sobre fe,
  tecnología y construir con agentes de IA
→ **Instagram**: [@onetogregorio](https://instagram.com/onetogregorio) —
  detrás de cámaras, cortes de predicación, pensamientos del día
→ **GitHub**: [@onetogregorio](https://github.com/onetogregorio)

Construido con [Claude Code](https://claude.com/claude-code).

---

## Licencia

MIT — vea [`LICENSE`](LICENSE). Úsalo libremente. Corta más mensajes. Alcanza más gente.
