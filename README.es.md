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

## Inicio rápido

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
→ **GitHub**: [@netogregorio](https://github.com/netogregorio)

Construido con [Claude Code](https://claude.com/claude-code).

---

## Licencia

MIT — vea [`LICENSE`](LICENSE). Úsalo libremente. Corta más mensajes. Alcanza más gente.
