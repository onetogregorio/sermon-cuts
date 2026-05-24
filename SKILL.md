---
name: sermon-cuts
description: "End-to-end pipeline for cutting vertical short-form clips from long sermon/preaching videos. Triggered when the user wants to cut a sermon, preaching, pregação, mensagem, or sermon-style talking-head video into multiple short verticals (Reels/Shorts/TikTok). Handles: download (YouTube or local), Groq Whisper transcription, VAD-aware natural cut boundaries, LLM-proposed cuts with narrative-arc scoring, MediaPipe face-tracking smooth pan, brand-style burned subtitles (gold Outfit Black + black outline + footer), LUFS audio normalization. User curates which proposed cuts to render; the rest is automatic."
---

# sermon-cuts — pipeline de cortes pra pregações

## Quando invocar

Você invoca essa skill quando o usuário pede coisas como:
- "vamos cortar essa pregação https://..."
- "corta a mensagem em N cortes de 1 minuto"
- "fazer cortes do sermão"
- "transcrever e cortar essa pregação pra Reels/Shorts"
- "achar os melhores beats dessa mensagem"

Aceita input como **URL do YouTube** OU caminho local de `.mp4`/`.mov`.

## Resultado final

Em `<project>/edit/cuts/<slug_da_mensagem>/`:
```
01-tema_do_corte.mp4
02-outro_beat.mp4
...
```

Cada cut é:
- **Vertical 1080×1920 @ 30fps** (scale + crop com tracking suave da face)
- **Legenda burned-in** brand-style (Outfit Black, gold `#fbc531`, outline preto 0.8, rodapé MarginV=50, 3-4 palavras/linha, sentence case)
- **Áudio normalizado** a -14 LUFS (padrão Insta/TikTok/Reels)
- **H.264 CRF 18 preset slow** (qualidade alta, arquivo razoável)

## Workflow (one-at-a-time mode — Neto prefere)

### Fase A — Ingest + análise (automática, ~1 min)

1. **`scripts/01_ingest.py <url-or-path>`** — baixa via yt-dlp (1080p ou melhor) OU copia local pra `memory/messages/<slug>/source.mp4`
2. **`scripts/02_transcribe.py`** — Groq Whisper-large word-level → `transcript.json`
3. **`scripts/03_vad_segments.py`** — silero-vad detecta pausas ≥0.8s → `vad.json` (fronteiras candidatas)

### Fase B — Proposta de cortes (LLM, ~30s)

4. **Você (Claude) lê** `transcript.json` + `vad.json` e propõe cortes seguindo `prompts/propose_cuts.md`. Output: `cuts_proposed.json` com `[{n, slug, start, end, theme, hook, conclusion, coherence_score, depends_on}]`
5. **Apresenta ao usuário** numa lista ranqueada por score. Ele escolhe quais aprovar.

### Fase C — Render por cut aprovado (~30-60s cada)

Pra cada cut aprovado:
6. **`scripts/05_validate_cut.py`** — confirma final natural (sem "porque nós" truncado). Se inválido, ajusta extendendo até próxima pausa válida do VAD.
7. **`scripts/06_build_srt.py`** — gera SRT brand-style do segmento
8. **`scripts/07_render_track.py`** — MediaPipe face detection (2 fps) + smoothing (2.5s moving avg) + crop dinâmico 1080×1920 → vertical sem legenda
9. **Burn legenda** (ffmpeg + subtitles filter + force_style)
10. **`scripts/08_audio_normalize.py`** — pyloudnorm -14 LUFS no áudio final
11. **Salva** em `<project>/edit/cuts/<slug>/NN-cut_slug.mp4` e mostra preview pro Neto

### Fase D — Iteração

Se ele rejeitar/pedir mudança em um cut:
- Correção de texto da legenda → edita `srt`, reburn (não refaz tracking)
- Trim de início/fim → re-rodar do passo 7
- Cut inteiro errado → marca rejected em `cuts_proposed.json`, propõe substituto

## Estrutura de arquivos

```
~/.claude/skills/sermon-cuts/
├── SKILL.md                 ← este arquivo
├── scripts/
│   ├── 01_ingest.py
│   ├── 02_transcribe.py
│   ├── 03_vad_segments.py
│   ├── 04_propose_cuts.py   ← stub que chama Claude com prompt
│   ├── 05_validate_cut.py
│   ├── 06_build_srt.py
│   ├── 07_render_track.py
│   ├── 08_audio_normalize.py
│   └── pipeline.sh          ← orquestrador end-to-end
├── config/
│   ├── force_style.txt
│   ├── function_words_pt.txt
│   └── render_defaults.yaml
├── prompts/
│   └── propose_cuts.md
└── memory/
    └── messages/
        └── <slug_mensagem>/
            ├── source.mp4
            ├── transcript.json
            ├── vad.json
            ├── cuts_proposed.json
            └── status.json     ← per-cut: proposed/approved/rendered/rejected
```

## Regras hard (não negociar com usuário)

1. **Vertical 1080×1920**. Source horizontal → `scale=-2:1920,crop=1080:1920` com tracking dinâmico de X via MediaPipe. **Nunca** letterbox, **nunca** scale+pad com blur background.
2. **Legenda sentence case**, jamais UPPERCASE.
3. **Outline preto 0.8**, FontSize 16, MarginV 50. Não inventar.
4. **Cut precisa ter arco completo**: hook → desenvolvimento → conclusão. Se LLM não consegue identificar conclusão clara, rejeita o cut.

## Decisões que devem ser deferidas ao usuário (não automatizar)

- Quais cortes aprovar (curadoria final)
- Correção de transcrição quando Whisper erra palavra técnica/teológica
- Override de tema/slug do cut

## Comandos de invocação típicos

```bash
# Pipeline completa, modo interativo (default)
~/.claude/skills/sermon-cuts/scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# Só ingest + transcribe + propose (sem render)
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --propose-only /path/local.mp4

# Renderizar cortes específicos já propostos
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --render-cuts 2,4,7 --slug vinde_a_mim

# Reaplicar só legenda (sem retracking) num cut já feito
~/.claude/skills/sermon-cuts/scripts/pipeline.sh --reburn-srt 2 --slug vinde_a_mim
```

## Brand style (referência local — também em ~/.claude/projects/.../memory/video_brand_style.md)

```
Palette:
  gold-warm  #fbc531  — texto da legenda
  pure-black #000000  — outline
  navy-deep  #192a56  — accent só (animações), nunca outline

Font: Outfit (Black, FontName=Outfit + Bold=1)

force_style:
  FontName=Outfit,FontSize=16,Bold=1,
  PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,
  BorderStyle=1,Outline=0.8,Shadow=0,
  Alignment=2,MarginV=50
```
