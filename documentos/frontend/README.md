# Build do bundle TipTap (rodar UMA vez em dev, ou sempre que mudar entry.js)

Produção (Portainer) não tem pipeline npm — o bundle é gerado aqui e **commitado**.

```bash
cd documentos/frontend
npm install   # lê o package.json já commitado neste diretório

npx esbuild entry.js --bundle --minify --format=iife \
    --outfile=../static/documentos/js/vendor/tiptap.bundle.min.js

# copiar também pro STATIC_ROOT local (fora do controle de versão, gerado
# pelo collectstatic) se estiver testando sem rodar collectstatic:
cp ../static/documentos/js/vendor/tiptap.bundle.min.js \
   ../../static/documentos/js/vendor/tiptap.bundle.min.js

# commitar o .min.js gerado; servido via collectstatic em produção
```

Depois de gerar, `node_modules/` fica fora do versionamento (`.gitignore`).
`package.json`, `entry.js`, este README e o `.min.js` são versionados.

## Paginação visual (PaginationPlus)

Desde a Fase 8, o bundle inclui `tiptap-pagination-plus` (tag `tiptap-v3`,
MIT), que desenha a régua de páginas A4 no editor de modelos
(`documentos/modelos/<id>/`). Config real em
`documentos/static/documentos/js/editor/editor-init.js` — margens em px
convertidas das mesmas margens ABNT de `documento_a4.css` (25/20/20/30mm).

**Limitação conhecida:** a régua é uma *aproximação* do PDF real, não uma
fonte de verdade. Duas causas de divergência já identificadas:
1. Fonte local (Windows costuma ter Times New Roman instalada) x produção
   (container só tem `fonts-dejavu`, substitui por Liberation Serif) — métricas
   de fonte diferentes podem mudar a quantidade de linhas por página.
2. O editor faz um round-trip do HTML pelo schema do ProseMirror (parse +
   re-render), que pode normalizar marcações de forma sutilmente diferente do
   HTML bruto usado no `page.pdf()` real.

Por isso o botão "Páginas" na toolbar permite ligar/desligar a régua
(`togglePagination`), e o PDF gerado via Playwright continua sendo a fonte de
verdade pra paginação final — não o editor.

## Recuo de parágrafo (IndentAttrs)

Desde a Fase A da régua, `entry.js` exporta `Extension` (de `@tiptap/core`)
além dos nós/marcas de sempre. `documentos/static/documentos/js/editor/indent-attrs.js`
usa esse `Extension` pra declarar `indentLeft`, `indentRight` e `indentFirstLine`
no nó `paragraph`, sem precisar redeclarar o nó inteiro (evita "Duplicate
extension names"). Serializa como `margin-left`/`margin-right`/`text-indent`
inline no HTML salvo — mesmo mecanismo de round-trip de negrito/cor/etc.

## Espaçamento entre linhas (LineHeightAttrs)

`documentos/static/documentos/js/editor/line-height-attrs.js` usa o mesmo
`Extension` de `@tiptap/core` pra declarar `lineHeight` no nó `paragraph`
(mesmo mecanismo do `IndentAttrsExtension`, arquivo separado por convenção de
"uma extensão por arquivo"). Presets fixos (0.5, 1.0, 1.15, 1.5, 2.0 — padrão
Word) vêm do backend via `espacamentos_linha` (`views_documentos.py`),
aplicados por parágrafo/bloco selecionado, não ao documento inteiro. `null`
(botão "Espaçamento padrão") omite o style e cai no `line-height: 1.5` fixo
de `.editor-a4-shell` (`documento_a4.css`).