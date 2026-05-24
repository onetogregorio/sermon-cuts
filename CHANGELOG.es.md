# Changelog

[English](CHANGELOG.md) · [Português](CHANGELOG.pt.md) · **Español**

## 0.1.0 — Release inicial (2026-05-23)

Primer release público. Pipeline end-to-end:

- `01_ingest.py` — yt-dlp o archivo local → source administrado
- `02_transcribe.py` — YouTube VTT (predeterminado) o Groq Whisper, a nivel de palabra
- `03_vad_segments.py` — detección de pausa silero-vad → candidatos de corte
- `04_propose_cuts.py` — prepara input del LLM para la propuesta de corte
- `05_validate_cut.py` — auto-extiende cortes que terminan en medio del pensamiento
- `06_build_srt.py` — subtítulos brand-style (3-4 palabras, function-word shift)
- `07_render_track.py` — face tracking MediaPipe + smooth pan + burn de subtítulos
- `08_audio_normalize.py` — pyloudnorm a -14 LUFS
- `pipeline.sh` — orquestador

Brand style predeterminado: Outfit Black, oro `#fbc531`, outline negro `0.8`,
sentence case, posición de pie de página. Vertical 1080×1920 @ 30fps.

Incluye un `SKILL.md` para integración con Claude Code.

Testeado con dos sermones en PT-BR (~28min cada uno):
- *Vinde a mim* (Mateo 11) — 12 candidatos de corte propuestos, 8 renderizados.
- *Derrubando as fortalezas da mente* — 10 cortes renderizados.

Case studies de muestra en `examples/`.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
