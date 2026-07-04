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