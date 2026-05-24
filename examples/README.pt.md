# Exemplos

[English](README.md) · **Português** · [Español](README.es.md)

Esta pasta mostra o que o pipeline produz, usando dois sermões reais em PT-BR
processados durante o desenvolvimento.

## `sample_cuts/`

Um único exemplo de output (comprimido pra tamanho do repo):

- `01-fortaleza_e_protecao_demo.mp4` (5.3 MB, 37s)
  Cut #1 de *"Derrubando as fortalezas da mente"*. Vertical 1080×1920,
  legendas brand (Outfit Black ouro + outline preto + posição de rodapé),
  face tracking, áudio normalizado. Esse é o output cru do pipeline,
  pronto pra upar no Reels/Shorts/TikTok.

> O repo só inclui uma demo pra ficar leve. Em uso real o pipeline
> produz 8-12 cortes desse tipo por sermão de ~30min.

## Case studies

### `case_destruindo_fortalezas.md`

Análise em markdown dos 10 cortes propostos pro sermão
*"Derrubando as fortalezas da mente"*, com o tema de cada corte, a
estrutura hook/desenvolvimento/conclusão, e os timestamps do source original.
Esse é o que um `cuts_proposed.json` parece como doc human-readable.

### `case_destruindo_fortalezas_takes.md`

Notas dos bastidores do pass de curadoria — quais cortes manter, quais
mergear, quais rejeitar e por quê.

## Transcrições de exemplo

### `vinde_transcript_sample.json` (~470 KB)

Transcrição em nível de palavra de *"Vinde a mim"* (Mateus 11), sermão de 27:44, no
schema produzido por `02_transcribe.py`. 4016 palavras. Use isso pra
inspecionar o formato ou pra testar scripts downstream sem re-rodar
transcrição.

### `destruindo_fortalezas_transcript_sample.json`

Mesmo shape, sermão diferente. ~38min.

## `srts_destruindo_fortalezas/`

Os 10 arquivos SRT produzidos por `06_build_srt.py` pros cortes de *Destruindo
fortalezas*. Mostra o brand-style chunking (3-4 palavras, function-word
shift, sentence case) em ação.

---

## Como reproduzir a demo

1. Bote um vídeo longo de sermão PT-BR em `sources/seu_sermao.mp4`
2. `./scripts/pipeline.sh sources/seu_sermao.mp4`
3. (Leia a transcrição + proponha cortes manualmente OU peça pro Claude)
4. `./scripts/pipeline.sh --render-cuts 1,2,3 --slug seu_sermao`

Cortes caem em `memory/messages/seu_sermao/renders/`.

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
