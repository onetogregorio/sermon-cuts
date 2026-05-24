# Glossário

[English](GLOSSARY.md) · **Português** · [Español](GLOSSARY.es.md)

Definições em linguagem direta dos termos que você vai ver nos docs,
prompts e mensagens de erro. Lê isso uma vez e o resto do projeto fica
mais fácil de entender.

---

## Anatomia do pipeline

**Pipeline** — a cadeia de scripts (`01_ingest` → `02_transcribe` →
… → `08_audio_normalize`) que transforma um sermão longo em clipes
verticais curtos. Cada script faz uma coisa e escreve no disco antes
de passar pro próximo.

**Skill** — o wrapper que permite agentes de IA (Claude Code, Cursor,
Cline, Aider, etc) invocarem o pipeline conversacionalmente. É só um
`SKILL.md` + a pasta `scripts/`. Quando você fala "corta essa
pregação" no Claude Code, ele lê o `SKILL.md` e roda os comandos
certos.

**Slug** — nome curto, computer-friendly, de um sermão (sem espaço,
sem acento). Exemplos: `vinde`, `derrubando_fortalezas`,
`mateus_11_domingo`. Todo sermão ganha seu próprio slug e seu próprio
diretório de trabalho.

**Diretório de trabalho** — `memory/messages/<slug>/`. Onde tudo de
um sermão vive: transcript, propostas de corte, SRTs, correções.

---

## Anatomia do corte

**Cut (corte)** — um clipe curto produzido a partir do sermão. Um
sermão de 30min tipicamente rende 8-12 cortes de 25-60 segundos cada.

**Hook (gancho)** — a frase de abertura do corte. Os primeiros 1-2
segundos que ou prendem o viewer ou perdem ele. Hook forte é concreto,
específico, surpreendente.

**Desenvolvimento** — o que acontece no meio. A história desenrola, o
ponto é construído, a analogia é explorada.

**Conclusão / payoff** — a frase final. Onde o corte aterrissa. Deve
resolver o que o hook prometeu — punchline, aplicação, citação bíblica.

**Coherence score** — rating de 0-10 que a LLM atribui pra cada corte
proposto baseado em quão bem hook + desenvolvimento + conclusão
encaixam como uma ideia self-contained.

---

## Legendas

**SRT** — `.srt` (SubRip Text) é o formato padrão de legenda. Texto
puro com número de cue, timestamps e texto. Sermon Cuts gera um SRT
por corte.

**Cue** — uma entrada de SRT. Tipicamente 3-4 palavras mostradas
juntas na tela por 0,5-2 segundos.

**Palavra-função** — palavras curtas como "de", "para", "com", "que",
"mas", "porque" que conectam ideias mas não carregam sentido sozinhas.
Cues nunca devem terminar nessas — o olho fica preso esperando a
próxima palavra. O chunker tem lógica pra shiftar pra frente.

**Forbidden ending** — palavra-função no fim de uma cue. O pipeline
tenta prevenir via shift; o que não dá pra shiftar é flagado pra
revisão humana.

**Hook boost** — o markup ASS `{\fs22\b1}` auto-adicionado na primeira
cue de cada corte. Faz a primeira linha um pouco maior + bold durante
o burn-in pra atrair o olho no scroll.

**Burn-in** — ato de embedar permanentemente a legenda nos pixels do
vídeo (vs. enviar o SRT separado). Uma vez burned, a legenda não pode
ser desligada.

**libass** — biblioteca que ffmpeg usa pra renderizar legendas
ASS/SRT em vídeo. Tem que estar compilada no seu build do ffmpeg pro
filtro `subtitles` funcionar.

**`force_style`** — string de estilização passada ao libass que
controla fonte, cor, outline, tamanho, posição. Vive em
`config/style_presets/*.txt`.

---

## Áudio

**LUFS** (Loudness Units Full Scale) — medida moderna de loudness
percebido. Instagram, TikTok, Reels e YouTube normalizam pra ~-14
LUFS, por isso esse é nosso target.

**True peak (dBTP)** — nível de pico real após reconstrução de áudio.
Diferente de sample peak. Targetamos -1.5 dBTP pra ter headroom e zero
clipping.

**Clipping** — quando áudio excede o nível máximo representável e fica
cortado, produzindo som distorcido "crunchy". O normalizer com true-peak
limit previne isso.

**Loudnorm** — filtro de normalização de loudness EBU R128 do ffmpeg.
Padrão da indústria pra broadcast e streaming.

---

## Tracking de vídeo

**Face tracking** — amostrar posição da face frame a frame e usar pra
decidir onde cortar o frame vertical. Mantém o pregador centralizado
mesmo quando ele anda pelo palco.

**MediaPipe** — toolkit ML open-source do Google. O pipeline usa o
detector de face BlazeFace short-range e o pose landmarker (pra
fallback no ombro quando face detection falha).

**VAD (Voice Activity Detection)** — algoritmo que identifica quais
partes do áudio têm fala vs. silêncio. Sermon Cuts usa
[silero-vad](https://github.com/snakers4/silero-vad) pra achar pausas
naturais onde os cortes podem aterrissar sem dividir palavra.

**Pan smoothing** — média das posições X da face numa janela de 2,5s
pra que o crop não treme conforme as detecções oscilam frame a frame.
Dá ao vídeo final uma sensação de pan "cinematográfico".

**Janela de crop** — janela de 1080 de largura cortada do frame source
(tipicamente 1920 de largura) pra produzir o vertical 1080×1920 final.

---

## Tech de vídeo

**BT.709** — padrão de color space pra vídeo HD. O Preview do macOS
recusa exibir vídeos H.264 corretamente se a metadata BT.709 não tá
explicitamente taggeada. O pipeline tagga em todo render.

**H.264 / libx264** — codec de vídeo usado no output. Padrão pra web
e plataformas sociais. CRF 18 (padrão) = visualmente lossless.

**Preset (slow/fast/etc)** — tradeoff de velocidade vs. tamanho do
encode do libx264. `slow` = arquivo menor na mesma qualidade, demora
mais. `fast` = arquivo maior, encoda mais rápido.

**MP4 / faststart** — formato container. `+faststart` reordena o
arquivo pra playback começar antes do download completo — essencial pra
streaming.

---

## Transcrição

**Whisper** — modelo speech-to-text open-source da OpenAI. Groq hosta
uma API de inferência rápida pra variante large (`whisper-large-v3`).

**Groq** — provedor de inferência third-party com API Whisper muito
rápida. Tier gratuita cobre a maioria do uso pessoal.

**VTT** (Web Video Text Tracks) — formato de legenda do YouTube.
Sermon Cuts parseia os arquivos VTT auto-gerados do YouTube quando
você usa `--provider=youtube`.

**yt-dlp** — ferramenta de linha de comando open-source pra baixar
vídeos e legendas do YouTube e várias outras plataformas.

---

## Arquivos & paths

**`sources/<slug>/source.mp4`** — seu vídeo cru do sermão (ou symlink
pra ele).

**`memory/messages/<slug>/`** — artifacts de trabalho pra um sermão
(transcript, VAD, propostas de corte, SRTs).

**`renders/<slug>/NN-slug.mp4`** — output do pipeline. Vertical,
legendado, áudio normalizado.

**`edit/cuts/<Nome do Sermão>/`** — sua pasta de curadoria pros
finais (conforme ritual do CLAUDE.md; convenção pessoal, gitignored).

**`config/`** — defaults do pipeline, listas de palavra-função,
presets de estilo, dicionários opcionais de correção.

**`prompts/`** — system prompts enviados pra LLM durante proposta de
corte e scrub de SRT.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
