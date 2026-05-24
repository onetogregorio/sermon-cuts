# Changelog

[English](CHANGELOG.md) · **Português** · [Español](CHANGELOG.es.md)

## 0.1.0 — Release inicial (2026-05-23)

Primeiro release público. Pipeline end-to-end:

- `01_ingest.py` — yt-dlp ou arquivo local → source gerenciado
- `02_transcribe.py` — YouTube VTT (padrão) ou Groq Whisper, em nível de palavra
- `03_vad_segments.py` — detecção de pausa silero-vad → candidatos de corte
- `04_propose_cuts.py` — prepara input do LLM pra proposta de corte
- `05_validate_cut.py` — auto-estende cortes que terminam no meio do pensamento
- `06_build_srt.py` — legendas brand-style (3-4 palavras, function-word shift)
- `07_render_track.py` — face tracking MediaPipe + smooth pan + burn de legenda
- `08_audio_normalize.py` — pyloudnorm pra -14 LUFS
- `pipeline.sh` — orquestrador

Brand style padrão: Outfit Black, ouro `#fbc531`, outline preto `0.8`,
sentence case, posição de rodapé. Vertical 1080×1920 @ 30fps.

Inclui um `SKILL.md` pra integração com Claude Code.

Testado com dois sermões em PT-BR (~28min cada):
- *Vinde a mim* (Mateus 11) — 12 candidatos de corte propostos, 8 renderizados.
- *Derrubando as fortalezas da mente* — 10 cortes renderizados.

Case studies de amostra em `examples/`.

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
