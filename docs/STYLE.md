# Style guide — sermon-cuts

[English](STYLE.en.md) · [**Português**](STYLE.md) · [Español](STYLE.es.md)

Defaults visuais opinionados que a skill `sermon-cuts` aplica em todo render. Leia antes de propor qualquer mudança em subtitle, animação ou layout. Pra overrides puramente locais (path de fonte, paleta alternativa de outra marca), use `CLAUDE.md` do projeto consumidor.

## Paleta de marca

| Token | Hex | RGB | Uso |
|---|---|---|---|
| `navy-deep` | `#192a56` | `(25, 42, 86)` | Accent — blocos de background, fills de animação. **Não** usar como outline de legenda. |
| `gold-warm` | `#fbc531` | `(251, 197, 49)` | Texto de legenda, highlights |
| `pure-black` | `#000000` | `(0, 0, 0)` | Outline de legenda — contraste limpo e nítido |

Codificação de cor ASS (Aegisub/libass usa `&HAABBGGRR`):
- `gold-warm` `PrimaryColour` = `&H0031C5FB`
- `pure-black` `OutlineColour` = `&H00000000`

## Tipografia

- **Família:** Outfit
- **Peso default:** 800 (Black)
- **ASS FontName:** `Outfit` (libass escolhe a variante Black quando `Bold=1`)
- Fallback se Outfit não estiver instalada: Helvetica Bold

A skill assume que `Outfit` está disponível no sistema (libass resolve pelo nome). Se você precisa apontar um `.ttf` específico no seu disco, sobrescreva `font_path` em `config/render_defaults.yaml` ou em `memory/messages/<slug>/overrides.yaml`.

## Regras de legenda

- **Nunca UPPERCASE.** Use sentence case ou caixa natural. Capitalize só a primeira palavra e nomes próprios.
- Chunking: 3–5 palavras por linha (não 2 — fica muito picotado pra Outfit Black que já é pesado).
- Texto: `gold-warm` `#fbc531`
- Outline: **preto** `#000000`, **`Outline=0.8`** (~5px no frame 1920) — fino, elegante, acompanha as letras sem pesar. Navy fica feio como outline — usar só pra blocos/animação.
- Sem shadow, sem background fill — deixa o outline carregar o contraste.
- `MarginV`: **50** — legenda no rodapé. Acima da barra de UI do Instagram/TikTok/Reels (que ocupa ~150–180px do fundo num frame 1920), mas posicionada como rodapé clássico, não no meio do peito.
- Alignment: 2 (centro inferior)

## String `force_style` reusável

```
FontName=Outfit,FontSize=16,Bold=1,
PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,
BorderStyle=1,Outline=0.8,Shadow=0,
Alignment=2,MarginV=50
```

**Tamanho real no frame vertical 1080×1920** (libass escala com base em PlayResY=288):
- `FontSize=16` → ~107 px de altura do texto (~5.5% da altura da tela)
- `Outline=0.8` → ~5 px de outline preto fino
- `MarginV=50` → legenda no rodapé, acima da UI do Insta/TikTok

Chunking padrão pra esse tamanho: **3–4 palavras por linha, máx ~20 chars** (Outfit Black é largo, quebra fácil).

A string completa também vive em `config/force_style.txt` pra consumo direto pelo `render.py`. Override por mensagem em `memory/messages/<slug>/overrides.yaml`.

## Paleta de animação (quando precisar)

Mesmas duas cores:
- Background ou fill: `navy-deep` `#192a56`
- Highlights, accents, text: `gold-warm` `#fbc531`
- Use Outfit Black em qualquer overlay de typography cinética.

Evite introduzir cores accent extras sem confirmar.

## Format default

**Vertical 1080×1920 @ 30fps. Sempre. Hard rule.** Não importa se o source é horizontal (16:9 de YouTube/palco) ou vertical de iPhone — o output final é **sempre** 1080×1920 cheio.

**Como converter source horizontal pra vertical:**

Use **scale + crop** (preenche o frame, corta as laterais). NUNCA scale + pad com fundo blurado, NUNCA letterbox horizontal no meio com barras pretas em cima/baixo — fica feio e amador.

Receita ffmpeg pra source 1920×1080 → 1080×1920:
```
-vf "scale=-2:1920,crop=1080:1920"
```

Isso escala mantendo aspect até a altura 1920 (largura vira ~3413), depois corta o centro 1080 de largura. O speaker fica grande, centralizado, preenche a tela.

Se o ponto de interesse não estiver no centro horizontal do source, ajuste o crop X manualmente (`crop=1080:1920:X:0`). Mas o default é centro — e o `07_render_track.py` resolve isso automaticamente via MediaPipe face tracking.

**O que NÃO fazer:**
- ❌ Vídeo horizontal pequeno no meio do frame vertical com fundo blurado em cima/baixo
- ❌ Letterbox com barras pretas
- ❌ Source horizontal renderizado como horizontal e depois rotacionado/encaixotado

## Organização de arquivos (cuts)

Cada **mensagem/sermão/conteúdo** ganha sua própria subpasta dentro de `edit/cuts/`. Os arquivos finais ficam diretamente na subpasta, nomeados com o padrão `NN-slug.mp4`:

```
edit/cuts/
├── Destruindo fortalezas/          ← nome da mensagem (humano-legível, pode ter espaços)
│   ├── 01-fortaleza_e_protecao.mp4
│   ├── 02-nenhum_pensamento_e_neutro.mp4
│   └── ...
└── <Outra mensagem>/
    ├── 01-tema.mp4
    └── ...
```

Regras do nome:
- Prefixo `NN-` com zero à esquerda (01, 02 … 10) — mantém ordem alfabética = ordem de corte
- Slug em `snake_case`, ASCII, descrevendo o beat (`fortaleza_e_protecao`, `perdao_no_varejo`)
- Sem `cut_`, `_VERTICAL`, `_LEGENDADO` ou qualquer sufixo de pipeline — o arquivo final é o que importa
- Extensão `.mp4`

Intermediários (EDLs, SRTs, frames de verify, render preview) ficam em `edit/edls/`, `edit/srts/`, `edit/verify/` etc. — fora de `cuts/`. A subpasta de cada mensagem em `cuts/` é só pra os finais que vão pra publicação.

---

Por [@netogregorio](https://github.com/netogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)
