# Walkthrough do pipeline

[English](PIPELINE.md) · **Português** · [Español](PIPELINE.es.md)

Cada script grava em `memory/messages/<slug>/` e é idempotente (re-executar
é seguro e pula trabalho concluído, a menos que use `--force`).

## 01_ingest.py

```bash
./scripts/01_ingest.py <youtube-url-ou-caminho-local> [--slug SLUG]
```

URL do YouTube → usa yt-dlp para baixar a melhor qualidade até 1080p como MP4.
Arquivo local → cria symlinks (ou copia se o symlink falhar).

Grava:
- `memory/messages/<slug>/source.mp4`
- `memory/messages/<slug>/meta.json` (URL/caminho/título/duração)

Derivação do slug: a partir do título do YouTube ou nome do arquivo (slugificado para snake_case).
Sobrescreva com `--slug`.

## 02_transcribe.py

```bash
./scripts/02_transcribe.py <slug> [--provider=youtube|groq] [--language=pt]
```

### YouTube (padrão, grátis, instantâneo)

Chama `yt-dlp --write-auto-subs --skip-download` para pegar o arquivo VTT de auto-legenda
que o YouTube gera para todo vídeo público. Analisa timestamps inline em nível de palavra
do VTT (aquelas tags `<HH:MM:SS.mmm>` entre palavras).

### Groq (pago-ish, qualidade superior)

Extrai áudio (mono 16kHz WAV), envia para Groq Whisper-large-v3 com
`timestamp_granularities=["word"]`. Retorna timestamps em nível de palavra.
Precisa de `GROQ_API_KEY` no env.

Saída (mesmo formato para ambos):

```json
{
  "words": [
    {"text": "Eu", "start": 1.95, "end": 2.12, "type": "word"},
    {"text": " ", "start": 2.12, "end": 2.13, "type": "spacing"},
    ...
  ],
  "language": "pt",
  "_provider": "youtube-vtt"  // ou "groq-whisper-large-v3"
}
```

## 03_vad_segments.py

```bash
./scripts/03_vad_segments.py <slug> [--min-silence 0.5]
```

Roda [silero-vad](https://github.com/snakers4/silero-vad) no áudio do
source (reamostrado para 16kHz mono). Detecta segmentos de fala → deriva
os silêncios entre eles → marca o ponto médio de cada silêncio ≥ 0.5s como
**ponto de corte candidato** (lugares onde um corte não vai dividir palavra/respiração).

Saída:

```json
{
  "speech": [{"start": 0.34, "end": 12.18}, ...],
  "silences": [{"start": 12.18, "end": 13.05, "duration": 0.87}, ...],
  "candidate_cut_points": [12.18, 28.71, ...]
}
```

## 04_propose_cuts.py

```bash
./scripts/04_propose_cuts.py <slug>
```

Empacota transcrição + VAD em um único `propose_input.json` e imprime
os caminhos que o LLM (Claude) deve ler, mais o prompt em
`prompts/propose_cuts.md`. **Este script não chama um LLM** — apenas
prepara inputs.

Espera-se que o LLM grave os cortes propostos em
`memory/messages/<slug>/cuts_proposed.json`.

Schema esperado para cada corte:

```json
{
  "n": 1,
  "slug": "filha_no_mercado",
  "start": 92.40,
  "end": 165.10,
  "duration_s": 72.7,
  "theme": "Relação vs missão — ilustração da filha no mercado",
  "hook": "Eu gosto de uma ilustração muito boa...",
  "development": "...",
  "conclusion": "Jesus pede que a gente vá COM ele, não pra ficar n'Ele",
  "coherence_score": 9.2,
  "tags": ["ilustracao", "relacionamento_com_deus"],
  "vad_aligned": true
}
```

Veja `prompts/propose_cuts.md` para a rubrica completa.

## 05_validate_cut.py

```bash
./scripts/05_validate_cut.py <slug> <cut_index> [--write-back] [--max-extend-s 8]
```

Confirma que a última palavra do corte não é um término proibido (configurável em
`config/render_defaults.yaml` — ex. "porque", "mas", "que", "para", "com",
"de"). Se for, tenta estender o fim até o próximo ponto de corte candidato do VAD
dentro de `max-extend-s` segundos onde a palavra não seja mais proibida.

`--write-back` aplica o patch no corte em `cuts_proposed.json`.

## 06_build_srt.py

```bash
./scripts/06_build_srt.py <slug> <cut_index>
```

Gera um SRT brand-styled a partir das palavras da transcrição no range do corte:

- 3-4 palavras por legenda, máx ~20 caracteres (configurável)
- Divide na pontuação (`. ! ?` hard, `, ; :` soft se a legenda tiver ≥3 palavras)
- Divide em pausa ≥0.5s se a legenda tiver ≥3 palavras
- Deslocamento consciente de palavra-função: se uma legenda termina com "para"/"com"/"que"/etc.,
  desloca para a próxima legenda (assim legendas nunca terminam em palavra-função)
- Capitaliza a primeira legenda
- Remove pontuação suave no final do texto da legenda

Grava `memory/messages/<slug>/srts/NN-slug.srt`.

## 06b_scrub_srt.py

```bash
./scripts/06b_scrub_srt.py <slug> <cut_index> [--agent-review]
                                              [--use-llm]
                                              [--auto-apply]
                                              [--dry-run]
                                              [--corrections PATH]
```

Passo de lint que roda **entre `06_build_srt` e `07_render_track``,
escaneando o SRT em busca dos padrões de erro mais comuns das auto-captions
do YouTube (fronteiras de frase com palavra dropada, hesitações duplicadas,
termos teológicos grafados errado). Permite consertar erros de transcrição
antes do burn-in — economiza um re-encode inteiro por typo.

### O que ele procura

1. **`dropped_word_boundary`** — palavra-função (em / que / de / etc.)
   logo antes de uma palavra capitalizada que não é nome próprio. O
   YouTube engoliu uma palavra numa fronteira de frase.
       `"do que Mas não"`  ←  era na real  `"do que nós. Mas não"`
   Tem whitelist de personagens/lugares bíblicos comuns e pronomes em
   português pra `"em Cristo"` e `"para Ele"` não dispararem falso positivo.

2. **`immediate_repetition`** — `\b(\w+)\s+\1\b` filtrado pra hesitações
   conhecidas (a, o, um, uma, que, eu, ele, ela, …) e palavras curtas.
   Pula repetição estilística separada por vírgula tipo `"cansa, cansa"`.

3. **`forbidden_ending`** — re-checa a lista `cut_validation.forbid_endings`
   por legenda (não só na fronteira do corte como o `05_validate_cut.py`).
   Só reporta; o fix geralmente é mover a palavra final pra próxima
   legenda, melhor feito manualmente.

4. **`dictionary`** — se `memory/messages/<slug>/corrections.txt` existir,
   aplica pares `errado=correto` automaticamente (um por linha, `#` pra
   comentário). Útil pra fixes recorrentes:
   ```
   Quisto=Cristo
   Espirito=Espírito
   ```

### Três caminhos de review

| Caminho | Quando usar |
|---|---|
| **`--agent-review`** (default em non-TTY com suspeitos) | O orquestrador (Claude Code / Cursor / …) está lendo stdout. 06b emite JSON estruturado com texto da cue prev/next, snippet word-level do transcript ao redor de cada suspeito, e o path pro `prompts/scrub_srt.md`. O agente lê o prompt, decide fixes, aplica via Edit tool, e retoma o pipeline com `--skip-scrub`. |
| **`--use-llm`** | Runs standalone (cron, nightly, sem agente atrelado). Chama Anthropic Claude (prefere `ANTHROPIC_API_KEY`) ou Groq Llama (`GROQ_API_KEY` fallback). O mesmo `prompts/scrub_srt.md` vira system prompt; o LLM retorna `{fixes: [{cue, new_text, reason}]}` que aplicamos no SRT. |
| **`--auto-apply`** | Só regras, confiança ≥ 0.85. Na prática só colapsa hesitações silenciosamente. Modo mais barato. |

### Outros modos

| Flag | Comportamento |
|---|---|
| (nenhuma, TTY)  | review interativo — prompt `y/n/edit/skip` por suspeito |
| `--dry-run`     | só reporta, nunca escreve o SRT |

O `pipeline.sh` integra esse passo automaticamente (interativo em TTY,
JSON `--agent-review` em non-TTY pra o agente orquestrador agir). Pula
com `--skip-scrub`:

```bash
./scripts/pipeline.sh --render-cuts 1,2 --slug minha_msg --skip-scrub
```

Escreve em `memory/messages/<slug>/srts/NN-slug.srt` in-place. JSON em stdout:

```json
{
  "ok": true,
  "srt": "...",
  "suspects": [
    {"cue": 27, "tc": "00:00:36,080", "text": "do que Mas não",
     "pattern": "dropped_word_boundary",
     "suggestion": "do que. Mas não",
     "confidence": 0.75, "applied": false}
  ],
  "applied_count": 0,
  "dry_run": false
}
```

## 07_render_track.py

```bash
./scripts/07_render_track.py <slug> <cut_index> [--no-subs]
```

Renderização em duas passes:

**Pass 1 — amostragem de posição da face.** A 2 fps (padrão), roda detector
MediaPipe BlazeFace short-range no frame do source. Registra o center-X
da maior face detectada. Fallback para Haar cascade do OpenCV se
o MediaPipe falhar.

**Suavização.** Média móvel de 2.5s (5 amostras) das posições X da face
remove jitter de detecção e dá um feel cinemático.

**Pass 2 — renderiza frame por frame.** Para cada frame do source:
1. Escala para altura 1920 preservando aspect (1920×1080 → 3413×1920)
2. Interpola X suavizado para o timestamp do frame atual
3. Corta 1080×1920 centrado nesse X (clamped aos limites do frame)
4. Pipe de raw BGR frames para ffmpeg fazer encoding H.264 (CRF 18 preset slow)

**Mux de áudio.** Combina vídeo encodado com o segmento de áudio do source.

**Burn de legenda.** Aplica filtro ffmpeg `subtitles=` com `force_style`
de `config/force_style.txt`. Pule com `--no-subs`.

Grava `memory/messages/<slug>/renders/NN-slug.mp4`.

## 08_audio_normalize.py

```bash
./scripts/08_audio_normalize.py <slug> <cut_index> [--target-lufs -14] [--in-place]
```

Mede loudness integrado com pyloudnorm (ITU-R BS.1770-4), aplica
ganho pra acertar o LUFS alvo. Re-encoda áudio para AAC 192k, copia stream de vídeo.

`--in-place` sobrescreve o render original. Caso contrário grava um
sibling `.normalized.mp4`.

## pipeline.sh

Orquestrador:

```bash
# Ingest + transcribe + VAD + prepare propose-input
./scripts/pipeline.sh "https://youtube.com/watch?v=XXX"

# Renderiza índices específicos end-to-end (validate + SRT + render + normalize)
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug meu_sermao

# Só re-burn de legendas (depois de corrigir transcrição) sem re-tracking
./scripts/pipeline.sh --reburn-srt 3 --slug meu_sermao
```

## Layout de diretório por mensagem

Após uma execução completa:

```
memory/messages/<slug>/
├── source.mp4              # symlink ou download
├── meta.json               # URL/título/duração
├── transcript.json         # nível de palavra com type=word/spacing
├── vad.json                # segmentos de fala + candidatos de corte
├── propose_input.json      # input combinado pro LLM
├── cuts_proposed.json      # output do LLM (você cura isso)
├── srts/
│   └── NN-slug.srt
└── renders/
    └── NN-slug.mp4         # final, pronto pra subir
```

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
