# Build do bundle TipTap (rodar UMA vez em dev)

Produção (Portainer) não tem pipeline npm — o bundle é gerado aqui e **commitado**.

```bash
cd documentos/frontend
npm init -y
npm i @tiptap/core @tiptap/starter-kit @tiptap/extension-text-align \
      @tiptap/extension-underline @tiptap/extension-table \
      @tiptap/extension-table-row @tiptap/extension-table-cell \
      @tiptap/extension-table-header esbuild

npx esbuild entry.js --bundle --minify \
    --outfile=../static/documentos/js/vendor/tiptap.bundle.min.js

# commitar o arquivo gerado; servido via collectstatic
```

Depois de gerar, `node_modules/` e `package*.json` podem ficar fora do versionamento
(adicionar ao .gitignore). Apenas `entry.js`, este README e o `.min.js` são versionados.
