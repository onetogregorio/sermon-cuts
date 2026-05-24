# Notas de transcrição

[English](TRANSCRIPTION_NOTES.md) · **Português** · [Español](TRANSCRIPTION_NOTES.es.md)

## Auto-legendas YouTube vs Groq Whisper

| | YouTube VTT | Groq Whisper-large-v3 |
|---|---|---|
| **Custo** | Grátis | Tier gratuita cobre a maioria; pago se for pesado |
| **Velocidade** | ~3 seg (só baixar VTT) | ~30 seg por 10 min de áudio |
| **Qualidade** | Boa mas erros em palavras raras | Precisão state-of-the-art |
| **Precisa de chave API** | Não | Sim (`GROQ_API_KEY`) |
| **Funciona offline** | Não | Não |
| **Idiomas** | Vários (auto-detect ou `--language`) | 99 idiomas |
| **Timestamps em nível de palavra** | Sim (tags inline `<HH:MM:SS.mmm>`) | Sim (`timestamp_granularities=["word"]`) |

### Erros comuns de auto-legendas do YouTube que já vimos (PT-BR)

Estes geralmente precisam de uma correção manual rápida após `06_build_srt.py`:

- **Frases coladas truncadas**: quando uma frase termina e outra
  começa no mesmo span de áudio, o YouTube pode dropar uma palavra.
  Exemplo: `superestimamos a missão. Mas a missão...` → `superestimamos a Mas`
- **Drops de palavra no meio da frase**: problema similar; YouTube favorece output
  compacto e às vezes perde um conector.
  Exemplo: `vem para uma relação, então...` → `vem para uma Então`
- **Termos específicos de sermão**: vocabulário teológico ocasionalmente
  mal-transcrito (ex. "Cristo" → "Quisto" em áudio com ruído).

Para conteúdo high-stakes (leituras pagas de patrocinador, release pública), prefira
`--provider=groq`. Para conteúdo diário high-volume (10+ cortes/dia de
sermões), YouTube VTT + correções manuais é mais rápido no geral.

## Schema de referência

Ambos os providers emitem o mesmo formato JSON:

```json
{
  "words": [
    {"text": "Eu",       "start": 1.95, "end": 2.12, "type": "word"},
    {"text": " ",        "start": 2.12, "end": 2.13, "type": "spacing"},
    {"text": "gosto",    "start": 2.13, "end": 2.48, "type": "word"},
    {"text": " ",        "start": 2.48, "end": 2.50, "type": "spacing"},
    {"text": "de",       "start": 2.50, "end": 2.62, "type": "word"},
    ...
  ],
  "language": "pt",
  "_provider": "youtube-vtt"
}
```

Entradas `type: "spacing"` são sintéticas — representam o gap entre
duas palavras consecutivas e são úteis para código downstream que precisa
distinguir limites de respiração/pausa de fala contígua.

## Adicionar um novo provider

Para adicionar ex. Deepgram ou AssemblyAI:

1. Adicione uma entrada nas opções `--provider` em `02_transcribe.py`
2. Implemente `transcribe_<nome>()` retornando `{words, language, _provider}`
3. Use `_to_scribe_shape()` para normalizar raw words → o shape acima

O pipeline downstream (VAD, propose, SRT, render) não se importa com qual
provider produziu a transcrição.

## Corrigindo erros de transcrição no loop

Após `06_build_srt.py` você pode:

1. Inspecionar `memory/messages/<slug>/srts/NN-slug.srt`
2. Identificar legendas suspeitas (geralmente: legenda curta com capitalização estranha
   no meio da frase, ou frase terminando sem ponto)
3. Corrigir o texto da legenda diretamente — os timestamps continuam válidos
4. Re-burn apenas: `./scripts/pipeline.sh --reburn-srt N --slug <slug>`
   (isso pula o re-tracking, economiza ~30s por corte)

Para trabalho high-volume, considere uma etapa de correção assistida por LLM:
peça ao Claude para escanear o SRT em busca de erros prováveis de transcrição e propor
correções — bem mais rápido do que revisar cada legenda à mão.

---

Por [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
