# GLOT — Refatoração Completa do App `documentos`

> **Para o Claude Code:** Este documento é o guia completo de refatoração do app `documentos`.
> Siga as fases NA ORDEM. Cada fase tem critérios de aceite obrigatórios — só avance quando
> todos estiverem verdes. Não commite código com critérios pendentes. Não pergunte sobre
> alternativas arquiteturais — todas as decisões já estão tomadas aqui.
> Convenções do projeto: tabs para indentação, snake_case em Python, camelCase em JS.

---

## AGENT — Instruções de comportamento

Você é um engenheiro sênior especialista em Django e TipTap. Seu papel nesta refatoração é:

1. **Antes de qualquer alteração**: ler os arquivos reais. Nunca assumir nomes de campos,
   URLs ou estruturas — sempre inspecionar o código existente primeiro.
2. **Diagnóstico completo antes do patch**: identificar TODOS os problemas de uma área
   antes de tocar em qualquer arquivo. Não corrija um problema e quebre outro.
3. **Critérios de aceite são obrigatórios**: teste você mesmo antes de commitar.
   Se um critério falhar, corrija no mesmo patch — não commite parcial.
4. **Legado**: qualquer arquivo, view, URL, template ou model que não esteja listado
   nas fases abaixo como "manter" deve ser removido.
5. **Commits**: um commit por fase, mensagem em português, padrão do projeto.
6. **Se travar**: documente o bloqueio em `BLOQUEIOS.md` na raiz e pare — não improvise.

---

## SKILL 1 — Auditoria inicial (rodar ANTES de qualquer alteração)

```bash
# 1. Estrutura atual do app
find apps/documentos -type f | sort

# 2. Models existentes
cat apps/documentos/models.py 2>/dev/null || find apps/documentos -name "models*.py" | xargs cat

# 3. Views existentes
find apps/documentos -name "views*.py" | xargs ls -la

# 4. URLs existentes
find apps/documentos -name "urls*.py" | xargs cat

# 5. Templates existentes
find apps/documentos/templates -type f | sort

# 6. Estáticos existentes
find apps/documentos/static -type f | sort

# 7. O que está registrado no settings
grep -n "documentos\|STATIC\|MEDIA\|CELERY\|REDIS" config/settings.py

# 8. O que está registrado nas URLs raiz
cat config/urls.py

# 9. Menu lateral (onde estão os itens de documentos)
grep -rn "documentos\|Upload de Documento\|Marcadores" apps/ --include="*.html" | grep -v ".pyc"

# 10. Formato do conteúdo salvo no banco (HTML ou JSON?)
python manage.py shell -c "
from apps.documentos.models import ModeloDocumento
m = ModeloDocumento.objects.first()
if m:
    print('TIPO:', type(m.conteudo_html))
    print('INÍCIO:', repr(m.conteudo_html[:200]))
else:
    print('Nenhum modelo no banco')
"
```

**Salve o output completo desta auditoria antes de continuar.**

---

## SKILL 2 — Mapeamento de legado (o que remover)

Após a auditoria, identificar e listar:

### Remover — Views legadas
Qualquer view que faça referência a:
- Upload de Documento (model antigo de upload)
- Marcadores
- Qualquer model que não esteja listado na Seção de Models abaixo
- `proposta_legado` (pode remover após confirmar que a nova proposta funciona)

### Remover — URLs legadas
- Qualquer rota que aponte para views removidas
- Manter apenas as URLs listadas na Seção de URLs abaixo

### Remover — Templates legados
- Templates que serviam as views removidas
- `modelo_editor.html` atual será reescrito nesta refatoração

### Remover — Models legados
- Qualquer model não listado na Seção de Models abaixo
- Gerar migration de remoção das tabelas órfãs

### Remover — Menu lateral
- Itens "Upload de Documento" e "Marcadores" do template do menu

### Manter
- Todos os models listados na Seção de Models abaixo
- Dados existentes no banco (ModeloDocumento, VariavelDocumento)
- Bundle TipTap em `static/documentos/js/vendor/tiptap.bundle.min.js`

---

## SKILL 3 — Geração/atualização do bundle TipTap

**Quando usar:** sempre que adicionar ou remover extensões TipTap.

```bash
# Criar pasta temporária FORA do repo
mkdir /tmp/tiptap-build && cd /tmp/tiptap-build
npm init -y
npm install \
  @tiptap/core \
  @tiptap/starter-kit \
  @tiptap/extension-text-align \
  @tiptap/extension-table \
  @tiptap/extension-table-row \
  @tiptap/extension-table-cell \
  @tiptap/extension-table-header \
  @tiptap/extension-color \
  @tiptap/extension-highlight \
  @tiptap/extension-subscript \
  @tiptap/extension-superscript \
  @tiptap/pm \
  esbuild
```

Criar `/tmp/tiptap-build/entry.js`:
```js
import { Editor, Node, Extension, mergeAttributes } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import Color from '@tiptap/extension-color'
import Highlight from '@tiptap/extension-highlight'
import Subscript from '@tiptap/extension-subscript'
import Superscript from '@tiptap/extension-superscript'
import { TextStyle } from '@tiptap/core'

// StarterKit v3+ já inclui Underline — NÃO importar separado (warning de duplicata)

window.TipTapBundle = {
  Editor, Node, Extension, mergeAttributes,
  StarterKit,
  TextAlign,
  Table, TableRow, TableCell, TableHeader,
  Color, TextStyle,
  Highlight,
  Subscript, Superscript,
}
```

```bash
cd /tmp/tiptap-build
npx esbuild entry.js --bundle --minify \
  --outfile=tiptap.bundle.min.js

# Copiar para o repo
cp tiptap.bundle.min.js /caminho/para/o/repo/apps/documentos/static/documentos/js/vendor/tiptap.bundle.min.js
```

Depois: `python manage.py collectstatic --noinput`

**Verificar:** abrir o editor, sem erro `Cannot read properties of undefined` no console.

---

## SKILL 4 — Cache-bust automático de estáticos

O helper `_asset_ver()` em `views_documentos.py` deve incluir TODOS os estáticos do editor:

```python
import os
from django.contrib.staticfiles.finders import find as static_find

def _asset_ver():
    """Retorna mtime máximo dos estáticos do editor para cache-bust."""
    arquivos = [
        'documentos/js/vendor/tiptap.bundle.min.js',
        'documentos/js/editor/variavel-node.js',
        'documentos/js/editor/editor-init.js',
        'documentos/css/documento_a4.css',
    ]
    mtime = 0
    for arq in arquivos:
        caminho = static_find(arq)
        if caminho:
            mtime = max(mtime, int(os.path.getmtime(caminho)))
    return str(mtime)
```

No template, todos os estáticos do editor devem ter `?v={{ asset_ver }}`:
```html
<link rel="stylesheet" href="{% static 'documentos/css/documento_a4.css' %}?v={{ asset_ver }}">
<script src="{% static 'documentos/js/vendor/tiptap.bundle.min.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/variavel-node.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/editor-init.js' %}?v={{ asset_ver }}"></script>
```

---

## FASE 1 — Auditoria e remoção de legado

### Passos
1. Rodar a SKILL 1 completa e salvar o output.
2. Com base no output, mapear legado conforme SKILL 2.
3. Remover views, URLs, templates e models legados.
4. Gerar migration para remover tabelas órfãs.
5. Remover itens "Upload de Documento" e "Marcadores" do menu lateral.
6. Verificar que o projeto sobe sem erros após as remoções.

### Critérios de aceite
- [ ] `python manage.py check` sem erros
- [ ] `python manage.py migrate` sem erros
- [ ] Menu lateral mostra apenas "Modelos" e "Variáveis" em DOCUMENTOS
- [ ] Nenhuma URL 500 em rotas de documentos que ainda devem existir
- [ ] Nenhum import de model/view removido em outros apps

---

## FASE 2 — Estabilizar o editor TipTap

### Problema raiz confirmado
O banco armazena `conteudo_html` como **HTML puro** (string HTML).
O editor TipTap deve ser inicializado com HTML, não JSON.
Esta é a fonte de todos os bugs de "editor abre vazio".

### 2.1 — Verificar formato do banco
```python
python manage.py shell -c "
from apps.documentos.models import ModeloDocumento
for m in ModeloDocumento.objects.all():
    c = m.conteudo_html
    print(f'id={m.id} | tipo={\"JSON\" if c.strip().startswith(\"{\") else \"HTML\"} | inicio={repr(c[:80])}')"
```

Se qualquer registro tiver JSON TipTap, migrar para HTML:
```python
# Em shell ou migration de dados
from apps.documentos.models import ModeloDocumento
import json

for m in ModeloDocumento.objects.all():
    c = m.conteudo_html.strip()
    if c.startswith('{'):
        # JSON TipTap — converter para HTML via heurística simples
        # ou marcar para revisão manual
        print(f'ATENÇÃO: id={m.id} tem conteúdo JSON — requer conversão manual')
```

### 2.2 — view `modelo_editor` (views_documentos.py)
```python
def modelo_editor(request, pk=None):
    if pk:
        modelo = get_object_or_404(ModeloDocumento, pk=pk)
        conteudo_html = modelo.conteudo_html or ''
        salvar_url = reverse('documentos:modelo-salvar', kwargs={'pk': pk})
        is_novo = False
    else:
        modelo = None
        conteudo_html = ''
        salvar_url = reverse('documentos:modelo-salvar-novo')
        is_novo = True

    variaveis = VariavelDocumento.objects.filter(ativo=True).order_by('categoria', 'ordem')
    variaveis_por_categoria = {}
    for v in variaveis:
        variaveis_por_categoria.setdefault(v.categoria, []).append({
            'slug': v.tag_slug,
            'label': v.label,
            'exemplo': v.exemplo,
        })

    return render(request, 'documentos/modelo_editor.html', {
        'modelo': modelo,
        'is_novo': is_novo,
        'salvar_url': salvar_url,
        # CRÍTICO: passar HTML puro como string JSON-escaped para o JS
        'conteudo_inicial': json.dumps(conteudo_html),
        'variaveis_json': json.dumps(variaveis_por_categoria),
        'asset_ver': _asset_ver(),
        'tipos': TipoDocumento.choices,
    })
```

### 2.3 — editor-init.js (inicialização correta com HTML)

```js
// Receber HTML do Django (passado como JSON string no template)
const conteudoInicial = JSON.parse(document.getElementById('conteudo-inicial').textContent || '""');

const editor = new T.Editor({
  element: document.querySelector('#editor-area'),
  extensions: [
    T.StarterKit,
    T.TextAlign.configure({ types: ['heading', 'paragraph'] }),
    T.Table.configure({ resizable: true }),
    T.TableRow,
    T.TableCell,
    T.TableHeader,
    T.TextStyle,
    T.Color,
    T.Highlight.configure({ multicolor: true }),
    T.Subscript,
    T.Superscript,
    VariavelNode,   // extensão customizada — carregada por variavel-node.js antes deste script
  ],
  // CRÍTICO: content como HTML string, não JSON
  content: conteudoInicial || '<p></p>',
  autofocus: true,
});
```

No template, passar o conteúdo via tag `<script type="application/json">`:
```html
<script type="application/json" id="conteudo-inicial">{{ conteudo_inicial }}</script>
```
(Nunca usar `{{ conteudo_inicial|safe }}` diretamente em atributo JS — XSS e quebra de string.)

### 2.4 — Autosave e salvamento manual

```js
let salvarUrl = JSON.parse(document.getElementById('salvar-url').textContent);
let autoSaveTimer = null;
let conteudoSalvo = editor.getHTML();
const isNovo = JSON.parse(document.getElementById('is-novo').textContent);

function salvar(redirecionar = false) {
  const payload = {
    titulo: document.getElementById('id_titulo').value.trim(),
    tipo: document.getElementById('id_tipo').value,
    conteudo_html: editor.getHTML(),
  };

  fetch(salvarUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '',
    },
    body: JSON.stringify(payload),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      conteudoSalvo = editor.getHTML();
      // Se era novo, atualizar URL para o pk criado
      if (data.salvar_url) {
        salvarUrl = data.salvar_url;
      }
      if (redirecionar && data.redirect) {
        window.location.href = data.redirect;
      }
    } else {
      alert('Erro ao salvar: ' + (data.erros || []).join('\n'));
    }
  })
  .catch(err => console.error('Erro ao salvar:', err));
}

// Autosave: só salva se houver mudança, só dispara em modelo existente após 1º save
editor.on('update', () => {
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    const atual = editor.getHTML();
    if (atual !== conteudoSalvo) {
      salvar(false);  // nunca redireciona no autosave
    }
  }, 30000);
});

// Botão salvar manual
document.getElementById('btn-salvar').addEventListener('click', () => salvar(true));
```

### 2.5 — variavel-node.js (sem alteração de conteúdo)
```js
const { Node, mergeAttributes } = window.TipTapBundle;

const VariavelNode = Node.create({
  name: 'variavel',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes() {
    return { slug: { default: '' } };
  },
  parseHTML() {
    return [{ tag: 'span[data-var]', getAttrs: el => ({ slug: el.getAttribute('data-var') }) }];
  },
  renderHTML({ node }) {
    return ['span', mergeAttributes({
      'data-var': node.attrs.slug,
      'class': 'doc-var',
    }), `{{ ${node.attrs.slug} }}`];
  },
  renderText({ node }) {
    return `{{ ${node.attrs.slug} }}`;
  },
});
window.VariavelNode = VariavelNode;
```

### 2.6 — Toolbar de tabela (aparece/some com isActive)

```js
const grupoTabela = document.getElementById('grupo-tabela');

function atualizarToolbar() {
  const dentroDeTabela = editor.isActive('table');
  grupoTabela.style.display = dentroDeTabela ? 'flex' : 'none';

  // Atualizar estado ativo dos botões básicos
  document.getElementById('btn-bold').classList.toggle('active', editor.isActive('bold'));
  document.getElementById('btn-italic').classList.toggle('active', editor.isActive('italic'));
  // ... demais botões
}

editor.on('selectionUpdate', atualizarToolbar);
editor.on('transaction', atualizarToolbar);
```

### 2.7 — Regenerar bundle
Rodar a SKILL 3 com as extensões listadas acima.

### Critérios de aceite — FASE 2
- [ ] Abrir modelo existente com conteúdo → editor mostra o conteúdo (não vazio)
- [ ] Abrir modelo novo → editor abre com `<p></p>` vazio, sem erro no console
- [ ] Clicar dentro de tabela → grupo de botões de tabela aparece
- [ ] Clicar fora de tabela → grupo de botões de tabela some
- [ ] Inserir variável pelo sidebar → aparece como chip azul no editor
- [ ] Autosave a cada 30s → não navega, não cria duplicata em modelo existente
- [ ] Botão Salvar → salva e redireciona para lista
- [ ] Zero erros no console ao abrir o editor
- [ ] Toolbar básica funciona: negrito, itálico, H1/H2, alinhamento, lista, tabela
- [ ] Toolbar expandida funciona: cor de texto, realce, sub/sobrescrito, hr, undo/redo, limpar

---

## FASE 3 — CSS A4 estável

O `documento_a4.css` deve cobrir todos os casos:

```css
/* === ÁREA DO EDITOR === */
.editor-a4-page {
  width: 210mm;
  min-height: 297mm;
  padding: 25mm 20mm 20mm 30mm;   /* margens ABNT */
  font-family: 'Times New Roman', Times, serif;
  font-size: 12pt;
  line-height: 1.5;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
  margin: 0 auto;
}

/* === TIPOGRAFIA JURÍDICA === */
.editor-a4-page h1,
.editor-a4-page h2 {
  text-align: center;
  font-size: 13pt;
  font-weight: bold;
  margin: 0.8em 0 0.4em;
}
.editor-a4-page p {
  text-align: justify;
  text-indent: 1.5cm;
  margin: 0.3em 0;
}
.editor-a4-page .clausula {
  text-align: justify;
  margin-bottom: 0.8em;
}

/* === ASSINATURA === */
.editor-a4-page .assinatura-bloco {
  display: flex;
  justify-content: space-around;
  margin-top: 2em;
}
.editor-a4-page .assinatura-linha {
  border-top: 1px solid #000;
  width: 180pt;
  text-align: center;
  padding-top: 4px;
  font-size: 11pt;
}

/* === TABELAS === */
.editor-a4-page table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}
.editor-a4-page table td,
.editor-a4-page table th {
  border: 1px solid #000;
  padding: 6px 10px;
  min-width: 40px;
  vertical-align: top;
}
.editor-a4-page table th {
  background-color: #f0f0f0;
  font-weight: bold;
  text-align: center;
}
.editor-a4-page .selectedCell {
  background-color: #dbeafe !important;
}
/* Redimensionamento de coluna */
.editor-a4-page .column-resize-handle {
  background-color: #adf;
  bottom: -2px;
  position: absolute;
  right: -2px;
  pointer-events: none;
  top: 0;
  width: 4px;
}
.tableWrapper { overflow-x: auto; }

/* === VARIÁVEIS === */
.doc-var {
  display: inline-block;
  background: #EEF4FF;
  border: 1px solid #BFDBFE;
  border-radius: 3px;
  padding: 0 4px;
  font-family: monospace;
  font-size: 11pt;
  color: #1d4ed8;
  white-space: nowrap;
  user-select: all;
}

/* === PDF (WeasyPrint) === */
@page {
  size: A4;
  margin: 25mm 20mm 20mm 30mm;
  @top-center { content: element(cabecalho); }
  @bottom-center { content: element(rodape); }
}
#cabecalho-pdf { position: running(cabecalho); }
#rodape-pdf { position: running(rodape); font-size: 9pt; text-align: center; }
```

### Critérios de aceite — FASE 3
- [ ] Editor mostra área branca com sombra, fonte Times New Roman
- [ ] Tabelas aparecem com bordas visíveis
- [ ] Variáveis aparecem como chips azuis
- [ ] Célula selecionada fica azul claro
- [ ] CSS não quebra o layout do AdminLTE ao redor do editor

---

## FASE 4 — Limpeza final e commit

1. Rodar `python manage.py check` — zero erros
2. Rodar `python manage.py migrate` — zero erros
3. Rodar `python manage.py collectstatic --noinput`
4. Testar manualmente o fluxo completo:
   - Criar modelo novo → salvar → reabre com conteúdo
   - Editar modelo existente ("Proposta de Compra e Venda") → conteúdo aparece → editar → salvar
   - Inserir tabela → manipular colunas/linhas → salvar → preview mostra tabela
   - Inserir variável → salvar → preview renderiza variável com valor de exemplo
   - Inativar modelo → aparece como "não" na lista → reativar → volta "sim"
5. Commit: `"Refatoração app documentos: remove legado, estabiliza editor TipTap"`

---

## URLs mantidas após a refatoração

```
/documentos/modelos/                        → lista de modelos
/documentos/modelos/novo/                   → editor (criar)
/documentos/modelos/<pk>/editar/            → editor (editar)
/documentos/modelos/<pk>/salvar/            → POST salvar existente
/documentos/modelos/salvar-novo/            → POST salvar novo
/documentos/modelos/<pk>/duplicar/          → POST duplicar
/documentos/modelos/<pk>/preview/           → preview com dados de exemplo
/documentos/modelos/<pk>/historico/         → versões do modelo
/documentos/modelos/<pk>/toggle-ativo/      → POST inativar/ativar
/documentos/variaveis/                      → lista de variáveis
/documentos/proposta/<uuid>/                → proposta via novo módulo
```

---

## Models mantidos após a refatoração

- `VariavelDocumento`
- `ModeloDocumento`
- `ModeloDocumentoHistorico`
- `EmpreendimentoDocumento`
- `ConfiguracaoDocumento`
- `DocumentoGerado`
- `SequencialDocumento`
- `Distrato`

**Remover** qualquer model legado não listado acima.

---

## Estrutura de arquivos esperada após a refatoração

```
apps/documentos/
├── __init__.py
├── admin.py
├── apps.py
├── models.py                          ← apenas os models listados acima
├── views_documentos.py                ← views do módulo (sem legado)
├── urls_documentos.py                 ← apenas URLs listadas acima
├── services.py                        ← lógica de negócio (renderizar, gerar, finalizar)
├── tasks.py                           ← Celery: gerar_pdf_documento
├── migrations/
├── static/documentos/
│   ├── css/
│   │   └── documento_a4.css
│   └── js/
│       ├── vendor/
│       │   └── tiptap.bundle.min.js   ← bundle commitado
│       └── editor/
│           ├── variavel-node.js
│           └── editor-init.js
└── templates/documentos/
    ├── modelo_lista.html
    ├── modelo_editor.html             ← reescrito nesta refatoração
    ├── modelo_preview.html
    └── pdf/
        └── documento_base.html
```

---

## Observações finais

- **Formato do conteúdo**: o banco usa HTML puro (`conteudo_html: TextField`).
  O TipTap recebe e devolve HTML. Nunca salvar JSON TipTap no banco.
- **Bundle TipTap**: sempre commitar o bundle gerado. Produção não tem NPM.
  Quando regenerar, usar a SKILL 3 deste documento.
- **DEBUG=False em dev**: sempre rodar `collectstatic` após alterar estáticos.
  O helper `_asset_ver()` garante que o browser baixe a versão nova.
- **Versões do modelo**: `save()` bumpa versão a cada mudança de `conteudo_html`.
  Autosave frequente pode inflar o histórico — tratar em sprint separado se necessário.
- **Autosave em modelo novo**: após o 1º save, a view retorna `salvar_url` com pk.
  O JS troca a URL para evitar criação de duplicatas.
