# GLOT — Debug: Arquivos Estáticos do Módulo de Documentos

## Contexto do projeto

Sistema Django chamado **GLOT** — ERP para gestão de loteamentos imobiliários.
Stack: Python/Django, PostgreSQL, Bootstrap/AdminLTE, Docker Swarm, Portainer.
Ambiente atual: desenvolvimento local no Windows (`python manage.py runserver`).

O módulo `documentos` foi reestruturado do zero recentemente.
Editor de modelos usa **TipTap vendorizado** (bundle commitado nos staticfiles, sem NPM em produção).

---

## Problema atual

O editor de modelos de documentos abre (`/documentos/modelos/<pk>/editar/`) mas
**não consegue salvar** — o TipTap nunca inicializa porque os arquivos estáticos
retornam `500 Internal Server Error` com MIME type `text/html` em vez dos
arquivos reais.

---

## Erros no Console do navegador (todos simultâneos ao abrir o editor)

```
Refused to apply style from
'http://127.0.0.1:8000/static/documentos/css/documento_a4.css'
because its MIME type ('text/html') is not a supported stylesheet type,
and strict MIME type checking is enabled.

GET http://127.0.0.1:8000/static/documentos/js/editor/variavel-node.js
net::ERR_ABORTED 500 (Internal Server Error)

GET http://127.0.0.1:8000/static/documentos/js/vendor/tiptap.bundle.min.js
net::ERR_ABORTED 500 (Internal Server Error)

Refused to execute script from
'http://127.0.0.1:8000/static/documentos/js/vendor/tiptap.bundle.min.js'
because its MIME type ('text/html') is not executable,
and strict MIME type checking is enabled.

Refused to execute script from
'http://127.0.0.1:8000/static/documentos/js/editor/variavel-node.js'
because its MIME type ('text/html') is not executable,
and strict MIME type checking is enabled.

GET http://127.0.0.1:8000/static/documentos/js/editor/editor-init.js
net::ERR_ABORTED 500 (Internal Server Error)

Refused to execute script from
'http://127.0.0.1:8000/static/documentos/js/editor/editor-init.js'
because its MIME type ('text/html') is not executable,
and strict MIME type checking is enabled.
```

---

## Diagnóstico

Quando Django retorna `text/html` para uma URL de arquivo estático,
significa que **o arquivo não existe no disco** e o Django está servindo
uma página de erro 500 (ou 404) no lugar.

Causas prováveis (verificar na ordem):

### 1. Arquivos não foram criados fisicamente
Os arquivos abaixo podem não existir no diretório `static/` do app:
```
apps/documentos/static/documentos/css/documento_a4.css
apps/documentos/static/documentos/js/vendor/tiptap.bundle.min.js
apps/documentos/static/documentos/js/editor/variavel-node.js
apps/documentos/static/documentos/js/editor/editor-init.js
```

O Claude Code pode ter criado a estrutura de diretórios mas não gerado
o conteúdo dos arquivos, ou pode ter referenciado caminhos errados.

### 2. Bundle do TipTap não foi gerado
O `tiptap.bundle.min.js` precisa ser gerado via esbuild uma vez em dev
e commitado. Pode nunca ter sido criado.

### 3. STATICFILES_DIRS ou app não registrado corretamente
Django pode não estar encontrando o diretório static do app documentos.

---

## O que fazer (passos para o Claude Code resolver)

### Passo 1 — Verificar o que existe no disco
```bash
# Listar o que há na pasta static do app documentos
find apps/documentos/static -type f 2>/dev/null || echo "Diretório não existe"

# Verificar settings
grep -n "STATIC" config/settings.py
grep -n "documentos" config/settings.py
```

### Passo 2 — Verificar o erro real do Django
Acessar diretamente no navegador:
```
http://127.0.0.1:8000/static/documentos/js/vendor/tiptap.bundle.min.js
```
Ver o HTML de erro retornado — vai mostrar o traceback real.

Ou no terminal com o servidor rodando, ver o output quando a página é carregada.

### Passo 3 — Criar os arquivos que faltam

#### 3a. Gerar o bundle do TipTap
Se o `tiptap.bundle.min.js` não existe, criar em pasta temporária fora do repo:
```bash
mkdir tiptap-build && cd tiptap-build
npm init -y
npm install @tiptap/core @tiptap/starter-kit @tiptap/extension-text-align \
  @tiptap/extension-table @tiptap/extension-table-row \
  @tiptap/extension-table-cell @tiptap/extension-table-header \
  @tiptap/extension-underline esbuild
```

Criar `entry.js`:
```js
import { Editor, Node, mergeAttributes } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'

window.TipTapBundle = {
  Editor, Node, mergeAttributes,
  StarterKit, TextAlign, Underline,
  Table, TableRow, TableCell, TableHeader
}
```

```bash
npx esbuild entry.js --bundle --minify \
  --outfile=tiptap.bundle.min.js
```

Copiar o arquivo gerado para:
```
apps/documentos/static/documentos/js/vendor/tiptap.bundle.min.js
```

#### 3b. Verificar/criar os outros arquivos JS e CSS
Se `variavel-node.js`, `editor-init.js` ou `documento_a4.css` não existem,
o Claude Code deve criá-los conforme o plano original
(`PLANO_MODULO_DOCUMENTOS.md`, Fases 6 e 7).

### Passo 4 — Verificar o template do editor
Confirmar que `templates/documentos/modelo_editor.html` referencia
os arquivos com `{% static %}` corretamente:
```html
{% load static %}
<link rel="stylesheet" href="{% static 'documentos/css/documento_a4.css' %}">
<script src="{% static 'documentos/js/vendor/tiptap.bundle.min.js' %}"></script>
<script src="{% static 'documentos/js/editor/variavel-node.js' %}"></script>
<script src="{% static 'documentos/js/editor/editor-init.js' %}"></script>
```

### Passo 5 — Confirmar que o salvamento funciona
Após os estáticos carregarem, o salvamento pode ter problema separado.
Verificar:
- View `salvar_modelo` existe e está mapeada na URL correta
- View recebe POST com `Content-Type: application/json`
- CSRF token está sendo enviado no fetch:
```js
headers: {
  'Content-Type': 'application/json',
  'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''
}
```

---

## Arquivos relevantes para inspecionar

```
apps/documentos/
├── static/documentos/          ← verificar se existe e o que tem dentro
├── templates/documentos/
│   └── modelo_editor.html      ← como os estáticos são referenciados
├── views.py                    ← view de edição e salvamento
└── urls.py                     ← mapeamento das URLs

config/settings.py              ← STATIC_URL, STATICFILES_DIRS, INSTALLED_APPS
```

---

## Estado atual do que funciona

- ✅ Editor abre (`/documentos/modelos/<pk>/editar/`)
- ✅ Título e tipo carregam corretamente
- ✅ Sidebar de variáveis renderiza (lista visível com cliente.nome, etc.)
- ✅ Toolbar de formatação aparece visualmente
- ❌ TipTap não inicializa (bundle não carrega)
- ❌ Salvamento não funciona
- ❌ CSS A4 não carrega (área do editor fica cinza sem formatação)

---

## Objetivo

Após resolver:
- Editor carrega com área A4 branca formatada
- Variáveis inseríveis via clique no sidebar (nó atômico azul)
- Botão Salvar funciona (POST JSON → view valida → salva no banco)
- Continuar os testes do plano original (`PLANO_MODULO_DOCUMENTOS.md`)
