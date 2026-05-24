# Cortes de Sermão

[English](README.md) · **Português** · [Español](README.es.md)

> **Skill pra Claude, Cursor e outros agentes de IA** que transforma vídeos
> longos de pregação, ministração, palestra ou ensino em cortes verticais
> prontos pra publicar no Reels, Shorts e TikTok — já enquadrados, legendados
> e com áudio nivelado. Cola o link do YouTube. Escolhe seus momentos favoritos.
> Recebe os cortes.

---

## O que você ganha

Você joga uma mensagem de 30, 40, até 60 minutos — sua pregação, sua palestra,
sua live — e sai com uma pasta de **shorts verticais prontos pra subir**. Cada um:

- Reenquadrado vertical (1080×1920) com o pregador centralizado, suave
- Legendado no seu estilo de marca — texto dourado, contorno limpo, sem CAIXA ALTA
- Balanceado pro loudness padrão das plataformas pra soar certo no Insta e TikTok
- Numerado, nomeado e organizado pra você saber o que postar e quando

O que era uma noite inteira de domingo no CapCut vira **~5 minutos de curadoria**.
Você decide o que publica. O pipeline faz o resto.

---

## Feito pra quem prega a Palavra

A maior parte das ferramentas de cortes pra short-form é feita pra marketeiro
vendendo tênis. Essa aqui é feita pra **pastor, pregador, evangelista, mestre,
criador de conteúdo cristão** — gente cuja mensagem merece mais do que uma
tarde corrida no Premiere.

Ela já sabe:

- Que um bom corte precisa de **hook**, **desenvolvimento** e **conclusão** —
  não só uma fatia aleatória de 60 segundos de alguém falando
- Que corte não pode terminar com "porque…" nem com "mas…" — tem que aterrissar
- Que a fonte da legenda importa, que o nível do áudio importa, que o
  enquadramento do rosto do pregador no frame vertical importa
- Que **você** é quem escolhe os cortes finais — a IA propõe, você decide

Nasceu com sermões em português em mente, mas funciona em qualquer idioma
(`--language=en`, `pt`, `es`, etc).

---

## Use como skill no seu editor de IA

O pipeline inteiro vem empacotado como skill do [Claude Code](https://claude.com/claude-code) —
ou seja, você fala com seu assistente de IA tipo:

> *"corta essa pregação: https://youtube.com/watch?v=…"*
> *"faz 8 cortes verticais dessa mensagem pro Instagram"*
> *"separa os melhores momentos desse vídeo pra Reels"*

…e o agente cuida da transcrição, da proposta de cortes, do rastreamento facial,
das legendas, da normalização de áudio e do render. Você só entra na parte que
importa: **escolher quais momentos da sua mensagem merecem virar conteúdo**.

Funciona igual com **Cursor**, **Cline**, **Aider** ou qualquer IDE/agente que
leia um `SKILL.md` e rode scripts.

---

## Instalar — escolha seu caminho

### 🟢 Mais fácil: um comando, qualquer terminal

```bash
curl -fsSL https://onetogregorio.github.io/sermon-cuts/install.sh | bash
```

Detecta seu sistema, instala ffmpeg/yt-dlp/Python, clona o repo, cria um
venv, symlinka a skill em `~/.claude/skills/sermon-cuts/`, opcionalmente
configura Groq + Outfit, e roda um health check no final. **Pode rodar
de novo sem medo** — não sobrescreve nada que já existe.

### 🟡 Através do seu editor de IA (Claude Code, Cursor, Codex…)

Cola esse prompt em qualquer editor com acesso ao terminal:

> Instala a skill **Sermon Cuts** (https://github.com/onetogregorio/sermon-cuts)
> na minha máquina. Me guia pelos passos abaixo e para se algum falhar:
>
> 1. Detecta meu sistema (macOS ou Linux). No macOS, garante Homebrew.
> 2. Instala deps de sistema: `ffmpeg` (com libass), `yt-dlp`, Python 3.12+.
> 3. Clona o repo pra `~/code/sermon-cuts` (ou me pergunta onde).
> 4. Cria venv Python dentro do repo e roda `pip install -r requirements.txt`.
> 5. Symlinka `scripts/`, `config/`, `prompts/` pra `~/.claude/skills/sermon-cuts/`
>    e copia o `SKILL.md` pra lá.
> 6. Me pergunta se quero transcrição melhor via Groq Whisper. Se sim,
>    abre https://console.groq.com/keys, pede a chave e adiciona
>    `GROQ_API_KEY=...` no `~/.env`.
> 7. Me pergunta se quero a fonte Outfit Black
>    (https://fonts.google.com/specimen/Outfit). Se sim, baixa e instala.
> 8. Roda `./scripts/pipeline.sh doctor` pra confirmar a instalação.
> 9. Me dá um exemplo de uma linha de como cortar meu primeiro sermão.
>
> Reporta sucesso ou o passo que falhou no final.

Depois do install, é só falar *"corta essa pregação: \<URL do YouTube\>"* pro mesmo agente.

### 🐳 Docker (Linux/Windows/sem pip)

```bash
docker run --rm \
  -v "$(pwd)/out:/work/memory/messages" \
  -e GROQ_API_KEY=$GROQ_API_KEY \
  ghcr.io/onetogregorio/sermon-cuts <url-do-youtube>
```

> Build local: `docker build -t sermon-cuts .` se quiser ajustar a imagem.

---

## Workflow do dia-a-dia — os quatro comandos que importam

```bash
pipeline.sh doctor                              # health check (rode esse primeiro)
pipeline.sh <url-ou-mp4>                        # ingest + transcreve + propõe cortes
pipeline.sh review <slug>                       # ↑↓ + SPACE + ENTER pra escolher + renderizar
pipeline.sh ui                                  # abre a UI web em localhost:7860
```

Ou, sem terminal nenhum:

```bash
pipeline.sh ui                                  # drag-drop, checkboxes, downloads
```

> 💡 **Sem chave Groq?** Deixa o `--provider=auto` escolher `local`
> (usa faster-whisper offline, sem API key, ~1× realtime em Apple Silicon)
> ou `youtube` (auto-captions, instantâneo, qualidade um pouco menor).

---

## Início rápido (manual)

Se preferir rodar na mão:

```bash
# 1. Baixa + transcreve + acha as pausas naturais  (~1 min num sermão de 30min)
./scripts/pipeline.sh "https://youtube.com/watch?v=ZKeORvbgWpA"

# 2. Claude (ou você) lê a transcrição e propõe ~10 cortes.
#    Aparece uma lista ranqueada; você escolhe quais renderizar.

# 3. Renderiza os cortes aprovados  (~30–60s por corte em Apple Silicon)
./scripts/pipeline.sh --render-cuts 1,2,4,7 --slug minha_pregacao
```

Os cortes finais aparecem em:

```
memory/messages/<slug>/renders/01-cut_slug.mp4
memory/messages/<slug>/renders/02-cut_slug.mp4
...
```

Vertical 1080×1920, legenda brand-style queimada, áudio a -14 LUFS — pronto pra
subir em Reels, Shorts ou TikTok. Veja [`examples/sample_cuts/`](examples/sample_cuts/)
pra um output real.

> Setup inicial: ver [INSTALL.md](docs/INSTALL.pt.md) — você precisa do `ffmpeg`,
> deps Python e um symlink único pros scripts da skill resolverem em
> `~/.claude/skills/sermon-cuts/`.

---

## O que tem dentro

Cada etapa é um script independente — combine como quiser, ou só roda
`pipeline.sh` end-to-end.

| Script | O que faz |
|---|---|
| `01_ingest.py` | URL do YouTube ou vídeo local → arquivo source gerenciado |
| `02_transcribe.py` | Transcrição em nível de palavra (grátis via YouTube, ou premium via Groq Whisper) |
| `03_vad_segments.py` | Acha pausas naturais pra cortes nunca dividirem palavra |
| `04_propose_cuts.py` | Empacota a mensagem pra IA propor cortes com arco narrativo |
| `05_validate_cut.py` | Conserta automaticamente cortes que terminam no meio do pensamento |
| `06_build_srt.py` | Legendas brand-style: 3-4 palavras, dourado, sentence case |
| `07_render_track.py` | Reenquadre vertical com tracking facial + legenda queimada |
| `08_audio_normalize.py` | Áudio nivelado a -14 LUFS (padrão Reels/TikTok) |
| `pipeline.sh` | Um comando pra rodar tudo |

Walkthrough completo em [`docs/PIPELINE.pt.md`](docs/PIPELINE.pt.md).
Instalação em [`docs/INSTALL.pt.md`](docs/INSTALL.pt.md).

---

## Instalação

```bash
# macOS
brew install ffmpeg yt-dlp python@3.12
pip install -r requirements.txt
```

(Instruções de Linux e setup opcional da API Groq em [`docs/INSTALL.pt.md`](docs/INSTALL.pt.md).)

---

## Faz parecer com a sua cara

Edita dois arquivos e o pipeline todo adota sua marca:

- `config/force_style.txt` — fonte, cor e posição da legenda
- `config/render_defaults.yaml` — resolução, frame rate, alvo de áudio

O estilo padrão é o look dourado-no-preto usado no conteúdo do
[netogregorio.com](https://netogregorio.com) — mas é todo seu pra mudar.

---

## Ver funcionando

Confere [`examples/`](examples/) pra dois case studies completos — os cortes
propostos, as decisões de curadoria, e os outputs verticais finais prontos
pra publicar.

Ou visita a [landing page do projeto](https://onetogregorio.github.io/sermon-cuts/pt/) →

---

## Patrocinadores

Construído com apoio de organizações investindo em ferramentas que servem a
igreja e os criadores de conteúdo cristão.

<!-- SPONSORS:START -->
- **[Midvash](https://midvash.com/pt-br)** — Bíblia online com IA · 9 idiomas,
  70 versões da Bíblia, busca semântica e ferramentas de estudo movidas a modelos de linguagem.
<!-- SPONSORS:END -->

Quer apoiar esse projeto? [Seja patrocinador →](https://github.com/sponsors/onetogregorio)

---

## Sobre mim

Oi, sou o **Neto Gregório** — construo ferramentas no cruzamento entre fé,
criatividade e IA. Fiz o Cortes de Sermão porque cansei de passar domingo à
noite cortando minhas próprias pregações pra Reels na mão, e imaginei que mais
gente pregando, ensinando e criando conteúdo cristão tava cansada também.

Se esse projeto te poupar uma noite, vou adorar saber.

→ **Blog**: [netogregorio.com](https://netogregorio.com) — textos sobre fé,
  tecnologia e construir com agentes de IA
→ **Instagram**: [@onetogregorio](https://instagram.com/onetogregorio) —
  bastidor, cortes de pregação, pensamentos do dia
→ **GitHub**: [@onetogregorio](https://github.com/onetogregorio)

Construído com [Claude Code](https://claude.com/claude-code).

---

## Licença

MIT — veja [`LICENSE`](LICENSE). Usa à vontade. Corta mais mensagens. Alcança mais gente.
