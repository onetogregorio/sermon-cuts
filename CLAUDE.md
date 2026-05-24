# Style defaults — Neto's video projects

Read these before proposing any subtitle, animation, or graphic style. Do not deviate without asking.

## Brand palette

| Token | Hex | RGB | Use |
|---|---|---|---|
| `navy-deep` | `#192a56` | `(25, 42, 86)` | Brand accent — background blocks, animation fills. **Not** for subtitle outline. |
| `gold-warm` | `#fbc531` | `(251, 197, 49)` | Subtitle text, accent highlights |
| `pure-black` | `#000000` | `(0, 0, 0)` | Subtitle outline — clean, sharp contrast |

ASS subtitle color encoding (Aegisub/libass uses `&HAABBGGRR`):
- `gold-warm` `PrimaryColour` = `&H0031C5FB`
- `pure-black` `OutlineColour` = `&H00000000`

## Typography

- **Font family:** Outfit
- **Default weight:** 800 (Black) — file at `/Users/netogregorio/Library/Fonts/Outfit-Black.ttf`
- **ASS FontName:** `Outfit` (libass picks the Black variant when `Bold=1`)
- Fallback if Outfit is missing: Helvetica Bold

## Subtitle rules

- **Never UPPERCASE.** Use sentence case or natural case. Capitalize the first word and proper nouns only.
- Chunking: 3–5 palavras por linha (não 2 — fica muito picotado pra Outfit Black que já é pesado).
- Text: `gold-warm` `#fbc531`
- Outline: **preto** `#000000`, **`Outline=0.8`** (~5px no frame 1920) — fino, elegante, acompanha as letras sem pesar. Navy fica feio como contorno — usar só pra blocos/animação.
- No shadow, no background fill — let the outline carry contrast.
- `MarginV`: **50** — legenda no rodapé. Acima da barra de UI do Instagram/TikTok/Reels (que ocupa ~150-180px do fundo num frame 1920), mas posicionada como rodapé clássico, não no meio do peito.
- Alignment: 2 (centro inferior)

## Reusable `force_style` string

```
FontName=Outfit,FontSize=16,Bold=1,
PrimaryColour=&H0031C5FB,OutlineColour=&H00000000,BackColour=&H00000000,
BorderStyle=1,Outline=0.8,Shadow=0,
Alignment=2,MarginV=50
```

**Tamanho real no frame vertical 1080×1920** (libass escala com base em PlayResY=288):
- `FontSize=16` → ~107 px de altura do texto (~5.5% da altura da tela)
- `Outline=0.8` → ~5 px de contorno preto fino
- `MarginV=50` → legenda no rodapé, acima da UI do Insta/TikTok

Chunking padrão pra esse tamanho: **3–4 palavras por linha, máx ~20 chars** (Outfit Black é largo, quebra fácil).

When rendering with `render.py`, pass this via the `SUB_FORCE_STYLE` env var or edit the constant in the script for this session.

## Animation palette (when needed)

Same two colors:
- Background or fill: `navy-deep` `#192a56`
- Highlights, accents, text: `gold-warm` `#fbc531`
- Use Outfit Black for any kinetic typography overlay.

Avoid introducing extra accent colors without asking.

## Format default

**Vertical 1080×1920 @ 30fps. Sempre. Hard rule.** Não importa se o source é horizontal (16:9 de YouTube/palco) ou vertical de iPhone — o output final é **sempre** 1080×1920 cheio.

**Como converter source horizontal pra vertical:**

Use **scale + crop** (preenche o frame, corta as laterais). NUNCA scale + pad com fundo blurado, NUNCA letterbox horizontal no meio com barras pretas em cima/baixo — fica feio e amador.

Receita ffmpeg pra source 1920×1080 → 1080×1920:
```
-vf "scale=-2:1920,crop=1080:1920"
```

Isso escala mantendo aspect até a altura 1920 (largura vira ~3413), depois corta o centro 1080 de largura. O speaker fica grande, centralizado, preenche a tela.

Se o ponto de interesse não estiver no centro horizontal do source, ajustar o crop X manualmente (`crop=1080:1920:X:0`). Mas o default é centro.

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
- Prefixo `NN-` com zero à esquerda (01, 02 ... 10) — mantém ordem alfabética = ordem de corte
- Slug em `snake_case`, ASCII, descrevendo o beat (`fortaleza_e_protecao`, `perdao_no_varejo`)
- Sem `cut_`, `_VERTICAL`, `_LEGENDADO` ou qualquer sufixo de pipeline — o arquivo final é o que importa
- Extensão `.mp4`

Intermediários (EDLs, SRTs, frames de verify, render preview) ficam em `edit/edls/`, `edit/srts/`, `edit/verify/` etc. — fora de `cuts/`. A subpasta de cada mensagem em `cuts/` é só pra os finais que vão pra publicação.
