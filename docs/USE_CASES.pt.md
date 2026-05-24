# Casos de uso — três fluxos concretos

[English](USE_CASES.md) · **Português** · [Español](USE_CASES.es.md)

O pipeline é o mesmo pra tudo, mas o ritmo muda por contexto. Escolhe
o fluxo mais perto do que você tá fazendo, segue o checklist, adapta
livremente.

---

## 1. Pregação de domingo (mais comum)

Você pregou hoje. Quer 5-10 clipes verticais no Reels e TikTok até
terça de manhã. ~45 minutos de trabalho total.

**Prep (10 min):**
- Sobe seu sermão pro YouTube (não-listado tá ok — auto-legenda é
  gerada de qualquer jeito após ~30 min).
- Confirma que o áudio do sermão tá claro (re-microfone se tiver chiado).
- Anota segmentos pra pular (avisos no começo, apelo no fim).

**Roda (5 min wallclock + ~1 min compute):**
```bash
./scripts/pipeline.sh "https://youtube.com/watch?v=SEU_VIDEO"
```
Isso ingere + transcreve + acha boundaries de pausa. Output: lista
ranqueada de ~10 cortes propostos.

**Cura (10-15 min):**
- Passa rápido na lista proposta (ranqueada por `coherence_score`).
- Pra cada candidato, lê o hook + conclusão em `cuts_proposed.json`.
- Aprova os 5-8 mais fortes.
- Rejeita qualquer um onde o hook precisa de contexto que não tá lá.

**Renderiza os aprovados (~5-10 min):**
```bash
./scripts/pipeline.sh --render-cuts 1,3,5,7,9 --slug <seu-sermao>
```
Cortes caem em `renders/<seu-sermao>/`. Cada um vertical 1080×1920,
legendado, áudio nivelado, pronto pra upar.

**Revisa (10 min):**
- Abre cada MP4 no QuickTime/VLC (não no Preview do macOS — veja
  TROUBLESHOOTING).
- Pra cada: assiste começo + fim, escuta clipping, confirma legenda
  batendo.
- Rejeita qualquer um que não aterrissa.

**Publica (5 min):**
- Move aprovados pra `edit/cuts/<Nome do Sermão>/`.
- Sobe pro seu agendador (Postiz, Hootsuite, uploads nativos).
- Caption cada um com o hook do `cuts_proposed.json` + seu CTA.

**Tempo real total:** ~45 min numa segunda tranquila. Na maioria das
semanas você vai confiar mais no pipeline e cortar 15 min da curadoria.

---

## 2. Série de 4 sermões (plano de release)

Você pregou uma série dominical de 4 partes. Quer release de conteúdo
da série em 8 semanas (~3 cortes por semana, rollout temático).

**Prep — uma vez:**
- Decide o schedule de release. Exemplo:
  - Semana 1: hook clip do sermão 1 + 2 clipes de apoio
  - Semana 2: clipe mais profundo do sermão 1 + bridge pro sermão 2
  - …etc.
- Escolhe convenção de slug. Exemplo: `serie_efesios_01`,
  `serie_efesios_02`, …
- Cria planilha de tracking: `cut_slug | data_release | plataforma |
  caption | hashtags | plays_7d`.

**Roda — por sermão:**
```bash
for n in 01 02 03 04; do
  ./scripts/pipeline.sh "https://youtube.com/watch?v=URL_${n}" \
    --slug serie_efesios_${n}
done
```

**Cura — uma vez, todos juntos:**
- Depois que os 4 sermões foram transcritos, abre os 4
  `cuts_proposed.json` lado a lado.
- Escolhe os 8 cortes mais fortes no total da série (não 8 por sermão
  — o objetivo é o ARCO da série).
- Mapeia cada corte pra sua data de release.

**Renderiza selecionados:**
```bash
./scripts/pipeline.sh --render-cuts 1,3,5 --slug serie_efesios_01
./scripts/pipeline.sh --render-cuts 2,6 --slug serie_efesios_02
# …etc
```

**Tip de rotação temática:** mantém um arquivo
`memory/hashtags/<tema>.txt` pra cada tema recorrente (fé, propósito,
oração, mente renovada, …) com 8-12 hashtags por tema. Rotaciona os
packs pelos cortes pra sua conta não ser flagada por hashtag spam.

---

## 3. Conferência multi-dia (vários palestrantes)

Você hospedou ou gravou uma conferência: 6 palestrantes, 2 dias, 12
sessões no total. Quer drip de conteúdo por 2-3 meses pra puxar gente
de volta pra registrar no próximo ano.

**Prep:**
- Separa a sessão de cada palestrante no seu próprio arquivo de vídeo
  (não mistura palestrantes num MP4 — face tracking enlouquece).
- Pega permissão escrita de cada palestrante antes de publicar cortes
  deles.
- Escolhe um slug por sessão: `conf2025_doe_jane_keynote`,
  `conf2025_smith_john_painel`, etc. Slugs longos OK — organização de
  pasta ganha de brevidade aqui.

**Por sessão:**
```bash
./scripts/pipeline.sh ~/conf2025/raw/<palestrante>_<sessao>.mp4 \
  --slug conf2025_<palestrante>_<sessao>
```
Nota: passar MP4 local (não URL do YouTube) pula transcrição via
YouTube e usa Groq automaticamente — garanta que `GROQ_API_KEY` tá
setada.

**Cura — escolhe os 5 cortes mais fortes por sessão.** Não release
todos — qualidade sobre quantidade pra conteúdo de conferência. Mira
30 cortes totais pro drip de 2 meses (~5 por sessão × 6 sessões).

**Consistência de marca:** se você tem marca do evento (logo, cor),
configura um preset de estilo custom em `config/style_presets/conf2025.txt`
e aponta `config/render_defaults.yaml` pra ele pela duração do drip.
Reverte pro padrão pra conteúdo pessoal.

**Atribuição de palestrante:** adiciona uma title card de abertura em
cada corte creditando o palestrante (nome + handle IG + qual sessão).
Isso vai além do que o pipeline faz — joga o MP4 no CapCut/DaVinci pra
esse overlay único. Deixa palestrantes felizes e mais propensos a
compartilhar.

---

## Dicas que valem pra todos os casos

### Melhorando qualidade do corte

- **Áudio source melhor = cortes melhores.** Source clippado ou com
  ruído machuca tanto precisão de transcrição quanto a escutabilidade
  do vídeo final. Re-microfone se conseguir.
- **Brieffa a LLM.** Se sua tradição ou estilo difere de um sermão
  cristão brasileiro, edita `prompts/propose_cuts.md` pra descrever o
  que torna um corte excelente pra SUA audiência.
- **Usa um `corrections.txt` por sermão** pra termos teológicos ou
  nomes próprios que sua transcrição erra consistentemente. Veja
  [PRIVACY.pt.md](PRIVACY.pt.md) e [FAQ.pt.md](FAQ.pt.md).

### Backup do seu trabalho

`memory/messages/<slug>/` e `edit/cuts/` são gitignored de propósito
(são grandes + às vezes privados). Mas você NÃO quer perder. Escolhe um:
- rsync pra disco externo (manual, esforço baixo): `rsync -av memory/
  /Volumes/Backup/sermon-cuts-memory/`
- Symlink iCloud Drive (sync, automático)
- Repo GitHub privado paralelo com LFS próprio

### Tracking do que funciona

Uma planilha simples com colunas `cut_slug | plataforma | data_release |
plays_7d | saves | shares` vai te ensinar em 4 semanas quais padrões
retêm na sua audiência. Ajusta a rubrica de proposta de corte em
`prompts/propose_cuts.md` baseado no que você aprende.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
