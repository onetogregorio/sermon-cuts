# Casos de uso — tres flujos concretos

[English](USE_CASES.md) · [Português](USE_CASES.pt.md) · **Español**

El pipeline es el mismo para todo, pero el ritmo cambia por contexto.
Elige el flujo más cercano a lo que estás haciendo, sigue el
checklist, adapta libremente.

---

## 1. Predicación de domingo (más común)

Predicaste hoy. Quieres 5-10 clips verticales en Reels y TikTok para
el martes en la mañana. ~45 minutos de trabajo total.

**Prep (10 min):**
- Sube tu sermón a YouTube (no-listado está bien — los auto-subtítulos
  se generan de cualquier modo después de ~30 min).
- Confirma que el audio de tu sermón se escucha claro (re-micrófono si
  hay ruido).
- Anota segmentos a saltar (anuncios al inicio, llamado al final).

**Ejecuta (5 min wallclock + ~1 min compute):**
```bash
./scripts/pipeline.sh "https://youtube.com/watch?v=TU_VIDEO"
```
Esto ingiere + transcribe + encuentra límites de pausa. Salida: una
lista ranqueada de ~10 cortes propuestos.

**Cura (10-15 min):**
- Mira rápido la lista propuesta (ranqueada por `coherence_score`).
- Para cada candidato, lee el hook + conclusión en
  `cuts_proposed.json`.
- Aprueba los 5-8 más fuertes.
- Rechaza cualquiera donde el hook necesita contexto que no se ve.

**Renderiza los aprobados (~5-10 min):**
```bash
./scripts/pipeline.sh --render-cuts 1,3,5,7,9 --slug <tu-sermon>
```
Los cortes caen en `renders/<tu-sermon>/`. Cada uno vertical 1080×1920,
subtitulado, audio nivelado, listo para subir.

**Revisa (10 min):**
- Abre cada MP4 en QuickTime/VLC (no en macOS Preview — ver
  TROUBLESHOOTING).
- Para cada uno: mira inicio + fin, escucha clipping, confirma
  subtítulos coincidiendo.
- Rechaza cualquiera que no aterriza.

**Publica (5 min):**
- Mueve los aprobados a `edit/cuts/<Nombre del Sermón>/`.
- Sube a tu programador (Postiz, Hootsuite, uploaders nativos).
- Caption cada uno con el hook de `cuts_proposed.json` + tu CTA.

**Tiempo real total:** ~45 min en un lunes tranquilo. La mayoría de
semanas confiarás más en el pipeline y reducirás 15 min de curación.

---

## 2. Serie de 4 sermones (plan de release)

Predicaste una serie dominical de 4 partes. Quieres release de
contenido de la serie a lo largo de 8 semanas (~3 cortes por semana,
rollout temático).

**Prep — una vez:**
- Decide el schedule de release. Ejemplo:
  - Semana 1: hook clip del sermón 1 + 2 clips de apoyo
  - Semana 2: clip más profundo del sermón 1 + bridge al sermón 2
  - …etc.
- Elige convención de slug. Ejemplo: `serie_efesios_01`,
  `serie_efesios_02`, …
- Crea spreadsheet de tracking: `cut_slug | fecha_release | plataforma
  | caption | hashtags | plays_7d`.

**Ejecuta — por sermón:**
```bash
for n in 01 02 03 04; do
  ./scripts/pipeline.sh "https://youtube.com/watch?v=URL_${n}" \
    --slug serie_efesios_${n}
done
```

**Cura — una vez, todos juntos:**
- Después de que los 4 sermones se transcribieron, abre los 4
  `cuts_proposed.json` lado a lado.
- Elige los 8 cortes más fuertes en total de la serie (no 8 por sermón
  — el objetivo es el ARCO de la serie).
- Mapea cada corte a su fecha de release.

**Renderiza seleccionados:**
```bash
./scripts/pipeline.sh --render-cuts 1,3,5 --slug serie_efesios_01
./scripts/pipeline.sh --render-cuts 2,6 --slug serie_efesios_02
# …etc
```

**Tip de rotación temática:** mantén un archivo
`memory/hashtags/<tema>.txt` para cada tema recurrente (fe, propósito,
oración, mente renovada, …) con 8-12 hashtags por tema. Rota los
packs entre los cortes para que tu cuenta no sea marcada por hashtag
spam.

---

## 3. Conferencia multi-día (varios oradores)

Hospedaste o grabaste una conferencia: 6 oradores, 2 días, 12 sesiones
en total. Quieres drip de contenido por 2-3 meses para atraer gente de
vuelta a registrarse para el próximo año.

**Prep:**
- Separa la sesión de cada orador en su propio archivo de video (no
  mezcles oradores en un MP4 — el face tracking enloquece).
- Obtén permiso escrito de cada orador antes de publicar sus cortes.
- Elige un slug por sesión: `conf2025_doe_jane_keynote`,
  `conf2025_smith_john_panel`, etc. Slugs largos están OK —
  organización de carpeta gana sobre brevedad aquí.

**Por sesión:**
```bash
./scripts/pipeline.sh ~/conf2025/raw/<orador>_<sesion>.mp4 \
  --slug conf2025_<orador>_<sesion>
```
Nota: pasar MP4 local (no URL de YouTube) salta la transcripción vía
YouTube y usa Groq automáticamente — asegúrate de que `GROQ_API_KEY`
esté seteada.

**Cura — elige los 5 cortes más fuertes por sesión.** No releases
todos — calidad sobre cantidad para contenido de conferencia. Apunta a
30 cortes totales para el drip de 2 meses (~5 por sesión × 6 sesiones).

**Consistencia de marca:** si tienes marca de evento (logo, color),
configura un preset de estilo custom en
`config/style_presets/conf2025.txt` y apunta
`config/render_defaults.yaml` a él por la duración del drip. Revierte
al predeterminado para contenido personal.

**Atribución de orador:** agrega una title card de apertura a cada
corte acreditando al orador (nombre + handle IG + qué sesión). Esto va
más allá de lo que el pipeline hace — pon el MP4 en CapCut/DaVinci
para ese overlay único. Mantiene oradores contentos y más propensos a
compartir.

---

## Tips que valen para todos los casos

### Mejorando calidad del corte

- **Mejor audio fuente = mejores cortes.** Fuente clipeada o ruidosa
  daña tanto la precisión de la transcripción como la escuchabilidad
  del video final. Re-micrófono si puedes.
- **Brief al LLM.** Si tu tradición o estilo difiere de un sermón
  cristiano brasileño, edita `prompts/propose_cuts.md` para describir
  qué hace un corte excelente para TU audiencia.
- **Usa un `corrections.txt` por sermón** para términos teológicos o
  nombres propios que tu transcriptor falla consistentemente. Ver
  [PRIVACY.es.md](PRIVACY.es.md) y [FAQ.es.md](FAQ.es.md).

### Backup de tu trabajo

`memory/messages/<slug>/` y `edit/cuts/` están gitignored a propósito
(son grandes + a veces privados). Pero NO quieres perderlos. Elige uno:
- rsync a disco externo (manual, esfuerzo bajo): `rsync -av memory/
  /Volumes/Backup/sermon-cuts-memory/`
- Symlink iCloud Drive (sync, automático)
- Repo GitHub privado paralelo con su propio LFS

### Tracking de lo que funciona

Una spreadsheet simple con columnas `cut_slug | plataforma |
fecha_release | plays_7d | saves | shares` te enseñará en 4 semanas
qué patrones retienen en tu audiencia. Ajusta la rúbrica de propuesta
de corte en `prompts/propose_cuts.md` basado en lo que aprendes.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
