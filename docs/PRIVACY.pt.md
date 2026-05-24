# Privacidade & tratamento de dados

[English](PRIVACY.md) · **Português** · [Español](PRIVACY.es.md)

Sermon Cuts é um pipeline local-first. O fluxo padrão mantém seu
vídeo e áudio inteiramente no seu computador. Esse documento é a
resposta honesta pra *"se eu rodar isso, quem vê o quê?"*.

---

## TL;DR pra pastor

- **Seu arquivo de vídeo nunca sai do seu computador** em nenhum provedor.
- **Seu áudio sai do seu computador APENAS** se você escolher
  `--provider=groq` pra transcrição.
- **O texto da transcrição** é enviado pro seu editor de IA (Claude,
  Cursor, etc) quando você pede pra ele propor cortes — mesma coisa que
  qualquer prompt que você colaria manualmente.
- **O MP4 final renderizado** fica local até você subir ele você mesmo.

Pra privacidade máxima: use `--provider=youtube` na transcrição e **não**
passe `--use-llm` no scrub. Resto é tudo local.

---

## Que dados cada etapa do pipeline toca

### `01_ingest.py` — pegando o vídeo source

| Fonte que você passa | O que sai da sua máquina |
|---|---|
| URL do YouTube | URL é consultada pelo `yt-dlp` pra baixar o vídeo. Tráfego YouTube padrão. |
| Arquivo `.mp4` local | Nada. Arquivo é symlinkado ou copiado pra `memory/messages/<slug>/source.mp4`. |

### `02_transcribe.py` — palavras com timestamps

| `--provider=` | O que sai da sua máquina |
|---|---|
| `youtube` (padrão) | URL do YouTube é consultada via `yt-dlp` pra baixar o VTT de auto-legenda. **Nenhum áudio é uploadado.** Legendas são parseadas localmente. |
| `groq` | O áudio completo do sermão é extraído pra WAV temporário e uploadado pra API Groq Whisper-large-v3 pra transcrever. Veja a [política de privacidade do Groq](https://groq.com/privacy-policy/). |

### `03_vad_segments.py` — encontrar pausas naturais

100% local. Roda [silero-vad](https://github.com/snakers4/silero-vad)
no áudio in-process. **Nenhum dado sai da sua máquina.**

### `04_propose_cuts.py` — pedindo cortes pra IA

Esse script em si NÃO chama nenhuma API — só prepara a transcrição e
dados do VAD pro seu editor de IA ler.

Quando você (ou seu editor) age no prompt:
- **O texto da transcrição + timestamps de candidatos VAD** são enviados
  pro provedor do seu editor de IA (Anthropic, OpenAI, etc) como parte
  do prompt.
- **Nenhum áudio** é enviado.
- O arquivo de vídeo não é enviado — só a representação em texto.

Se seu editor de IA permite escolher modelo (ex. claude-haiku vs
claude-opus), você pode usar um modelo menor pra economizar; o texto
transcrito compartilhado é o mesmo.

### `05_validate_cut.py` — checar boundary limpo do corte

100% local. Lê transcript + VAD + cuts JSON, escreve de volta no disco.

### `06_build_srt.py` — gerar o arquivo de legenda

100% local. Sem acesso à internet.

### `06b_scrub_srt.py` — lint do SRT em busca de erros de transcrição

| Modo | O que sai da sua máquina |
|---|---|
| Padrão (só rule-based) | Nada. Padrões regex rodam localmente. |
| `--use-llm` | O texto do SRT + um prompt curto são enviados ou pra Anthropic (se `ANTHROPIC_API_KEY` setada) ou pro Groq (se `GROQ_API_KEY` setada). |
| `--agent-review` | Nada automaticamente. Escreve um prompt estruturado pro seu editor de IA interativo ler. |

### `07_render_track.py` — face tracking e queimar legenda

100% local. MediaPipe roda in-process. Na primeira execução, baixa o
modelo BlazeFace (~10 MB) de `storage.googleapis.com/mediapipe-models/`
— depois disso, sem acesso à internet.

### `08_audio_normalize.py` — nivelar áudio a -14 LUFS

100% local. Filtro `loudnorm` do ffmpeg faz tudo.

### `09_trim_silences.py` — remoção opcional de silêncio morto

100% local.

---

## A receita de privacidade máxima

Se você quer **zero dado saindo da sua máquina** além da URL do
YouTube em si, rode:

```bash
# Transcreve localmente (ou via VTT do YouTube — que é só consulta de URL)
./scripts/02_transcribe.py <slug> --provider=youtube

# Roda a proposta de cortes você mesmo, lendo a transcrição manualmente
# em vez de via Claude/Cursor — ou usa um LLM local (ollama, llama.cpp)

# Pula --use-llm no scrub
./scripts/06b_scrub_srt.py <slug> <n>     # sem flag --use-llm

# Renders são locais por design
./scripts/07_render_track.py <slug> <n>
./scripts/08_audio_normalize.py <slug> <n>
```

Se sua fonte é um `.mp4` local (não YouTube), a consulta de URL some
também — **fully air-gapped** do início ao fim.

---

## O que fica armazenado na sua máquina

O pipeline escreve tudo em dois diretórios no seu computador:

```
sources/<slug>/source.mp4          # ou symlink pro seu original
memory/messages/<slug>/
├── transcript.json                # timestamps em nível de palavra
├── vad.json                       # segmentos de pausa/fala
├── cuts_proposed.json             # propostas de corte da IA
├── corrections.txt                # suas correções de SRT por-sermão
├── srts/NN-slug.srt              # arquivos de legenda queimados
└── (nenhum arquivo de áudio é armazenado separadamente)

renders/<slug>/
└── NN-slug.mp4                    # clipes verticais finais
```

Tudo isso fica na sua máquina. O pipeline nunca sobe nada disso pra
servidor remoto. Se você quer backup, você é responsável (veja o ritual
no CLAUDE.md pra uma abordagem: rsync pra disco externo ou iCloud).

---

## O que NÃO é coletado

O pipeline tem **zero telemetria**. Sem analytics, sem error reporting,
sem stats de uso. Ele não liga pra casa. As únicas chamadas de rede são
as listadas neste documento, todas disparadas por flags de linha de
comando que você escolheu explicitamente.

---

## Notas específicas por provedor

### Groq Whisper

Quando você opta via `--provider=groq`:
- O chunk completo de áudio é uploadado.
- Conforme a [política do Groq](https://groq.com/privacy-policy/), eles
  retêm inputs por um período curto pra monitoramento de abuso; eles
  não (nessa data) usam inputs de API pra treinar modelos.
- Se você lida com conversas pastorais sensíveis (aconselhamento,
  gravações de oração), considere se a conveniência vale a pena.

### Anthropic / OpenAI (via seu editor de IA)

Quando você usa Claude Code, Cursor, etc:
- Você já tá sujeito aos termos de privacidade existentes deles.
- Texto da transcrição é enviado — sem áudio.
- Políticas de retenção e treinamento deles se aplicam.

### YouTube (yt-dlp)

Quando você passa uma URL do YouTube:
- A URL é consultada.
- Pra `--provider=youtube`, só o arquivo de auto-legenda é baixado.
- Pra `--provider=groq`, o vídeo é baixado localmente (pra ser
  re-encodado em áudio).
- Nenhum dado pessoal seu é enviado pro YouTube além do que seu IP já
  revela.

---

## Dúvidas

Abra uma issue no [GitHub](https://github.com/onetogregorio/sermon-cuts/issues)
ou contato via [netogregorio.com](https://netogregorio.com).

---

Escrito por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
