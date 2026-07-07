# Controle de fonte (família + tamanho) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar dois dropdowns na toolbar do editor de modelos (família de fonte + tamanho), aplicando no texto selecionado via atributos customizados na mark `textStyle` já existente.

**Architecture:** Extensão TipTap nova (`font-attrs.js`, mesmo padrão do `indent-attrs.js` da régua) adiciona `fontFamily`/`fontSize` como atributos globais na mark `textStyle` via `Extension.addGlobalAttributes`. Aplica via `editor.chain().focus().setMark('textStyle', {...}).run()` — comando genérico do `@tiptap/core` que já mescla com atributos existentes da mark (mesmo mecanismo que já faz `Color`/`Highlight` conviverem hoje).

**Tech Stack:** TipTap v3 (`window.TipTapBundle.Extension`, já exportado desde a Fase A da régua — nenhum rebuild de bundle necessário), Django (view finas), pytest-django + pytest-playwright (fixtures já existentes em `documentos/tests/conftest.py`).

## Global Constraints

- Nenhuma dependência npm nova — `Extension` já vem do bundle existente.
- Nenhuma migration, nenhum endpoint novo — formatação é só HTML inline no `conteudo_html`, salva pelo fluxo de save/autosave já existente.
- Fontes: lista fixa de 6 — DejaVu Serif, DejaVu Sans, DejaVu Mono, Liberation Serif, Liberation Sans, Liberation Mono. Nenhuma fonte fora dessa lista.
- Tamanhos: lista fixa de 9 — 9, 10, 11, 12, 14, 16, 18, 20, 24 (pt).
- JS: tabs, sem ponto-e-vírgula desnecessário, `const`/`let`, camelCase.
- Python: tabs, PEP 8.
- Após qualquer mudança em arquivo estático (`.js`), rodar `python manage.py collectstatic --noinput` antes de testar no navegador — `STATIC_ROOT` não atualiza sozinho (bug já mordeu esta sessão duas vezes).
- Cada tarefa termina com commit próprio, sem push.

---

### Task 1: Contexto de fontes na view do editor

**Files:**
- Modify: `documentos/views_documentos.py:106-131` (view `modelo_editor`)
- Test: `documentos/tests/test_views_modelo_editor_context.py` (arquivo já existe da régua — adicionar teste novo nele)

**Interfaces:**
- Produces: contexto `fontes_familia` (lista de tuplas `(valor_css, rotulo)`) e `fontes_tamanho` (lista de int) disponíveis no template `modelo_editor.html`.

- [ ] **Step 1: Escrever o teste (falhando)**

Adicionar ao fim de `documentos/tests/test_views_modelo_editor_context.py` (mesmo arquivo, mesma classe de setup já usada pelas outras — se preferir, criar um teste solto fora de classe usando `self.client`/`self.user` de uma nova instância mínima; siga o padrão abaixo, que reaproveita `TestCase` isolado):

```python
class ModeloEditorFontesContextTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_fontes_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.modelo = ModeloDocumento.objects.create(
			titulo='Contrato Fontes Teste', tipo=TipoDocumento.CONTRATO,
			conteudo_html='<p>Teste</p>', criado_por=self.user,
		)

	def test_editor_lista_fontes_e_tamanhos_fixos(self):
		url = reverse('documentos:modelo-editor', args=[self.modelo.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(
			[valor for valor, _rotulo in resp.context['fontes_familia']],
			['DejaVu Serif', 'DejaVu Sans', 'DejaVu Mono', 'Liberation Serif', 'Liberation Sans', 'Liberation Mono'],
		)
		self.assertEqual(resp.context['fontes_tamanho'], [9, 10, 11, 12, 14, 16, 18, 20, 24])
		self.assertContains(resp, 'DejaVu Serif')
		self.assertContains(resp, '24pt')
```

(Este teste usa `User`, `TipoDocumento`, `ModeloDocumento`, `reverse`, `TestCase` já importados no topo do arquivo pelos testes anteriores da régua — não precisa adicionar imports novos.)

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python manage.py test documentos.tests.test_views_modelo_editor_context.ModeloEditorFontesContextTest -v 2`
Expected: FAIL (`KeyError: 'fontes_familia'`)

- [ ] **Step 3: Adicionar o contexto na view**

Em `documentos/views_documentos.py`, dentro do dicionário retornado por `modelo_editor` (logo após a chave `'cores_realce'`, antes do `})` de fechamento, adicionar:

```python
		'fontes_familia': [
			('DejaVu Serif', 'DejaVu Serif'),
			('DejaVu Sans', 'DejaVu Sans'),
			('DejaVu Mono', 'DejaVu Mono'),
			('Liberation Serif', 'Liberation Serif'),
			('Liberation Sans', 'Liberation Sans'),
			('Liberation Mono', 'Liberation Mono'),
		],
		'fontes_tamanho': [9, 10, 11, 12, 14, 16, 18, 20, 24],
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python manage.py test documentos.tests.test_views_modelo_editor_context.ModeloEditorFontesContextTest -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add documentos/views_documentos.py documentos/tests/test_views_modelo_editor_context.py
git commit -m "feat(documentos): add fixed font family/size lists to modelo editor context"
```

---

### Task 2: Extensão de fonte + dropdowns na toolbar + aplicação

**Files:**
- Create: `documentos/static/documentos/js/editor/font-attrs.js`
- Modify: `documentos/templates/documentos/modelo_editor.html:66-88` (novo grupo de dropdowns na toolbar, antes do dropdown de cor) e `:191-195` (novo `<script>`)
- Modify: `documentos/static/documentos/js/editor/editor-init.js:69-99` (`criarExtensoes`), `:279-322` (switch de `data-action`), e adicionar wiring novo perto de `[data-color]`/`[data-highlight]` (linhas 335-348)
- Test: `documentos/tests/test_editor_font_attrs.py` (novo)

**Interfaces:**
- Consumes: `window.TipTapBundle.Extension` (já existe desde a Fase A da régua), contexto `fontes_familia`/`fontes_tamanho` (Task 1).
- Produces: `window.FontAttrsExtension` — extensão TipTap que adiciona `fontFamily`/`fontSize` (string ou `null`) à mark `textStyle`, serializados como `font-family`/`font-size` inline.

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/test_editor_font_attrs.py`:

```python
import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Fonte Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto de teste pra fonte e tamanho.</p>',
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_cor_fonte_e_tamanho_convivem_no_mesmo_span(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.commands.setTextSelection({ from: 1, to: 10 })
			window._editor.chain().focus().setColor('#dc3545').run()
			window._editor.chain().focus().setMark('textStyle', { fontFamily: 'DejaVu Serif' }).run()
			window._editor.chain().focus().setMark('textStyle', { fontSize: '14pt' }).run()
		}
	''')
	html = page.evaluate('window._editor.getHTML()')
	assert 'color:' in html.replace(' ', '') or 'color: #dc3545' in html
	assert 'font-family: DejaVu Serif' in html
	assert 'font-size: 14pt' in html
	assert 'Texto de teste pra fonte' in html


@pytest.mark.django_db
def test_remover_fonte_preserva_cor(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.commands.setTextSelection({ from: 1, to: 10 })
			window._editor.chain().focus().setColor('#dc3545').run()
			window._editor.chain().focus().setMark('textStyle', { fontFamily: 'DejaVu Serif' }).run()
			window._editor.chain().focus().setMark('textStyle', { fontFamily: null }).run()
		}
	''')
	html = page.evaluate('window._editor.getHTML()')
	assert 'font-family:' not in html
	assert '#dc3545' in html
```

(`documentos/tests/conftest.py` já existe da régua — `superuser`/`logged_browser` reaproveitados sem mudança.)

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest documentos/tests/test_editor_font_attrs.py -v`
Expected: FAIL (`TypeError` — `setMark` com atributo `fontFamily` não reconhecido, ou o atributo não aparece no HTML)

- [ ] **Step 3: Criar a extensão de fonte**

Criar `documentos/static/documentos/js/editor/font-attrs.js`:

```js
// Extensão FontAttrs — adiciona família e tamanho de fonte à mark
// "textStyle" (já usada por Color/Highlight) sem redeclarar a mark inteira.
// null = não define (renderHTML omite o style, mesmo idioma do indent-attrs.js).
(function () {
	if (!window.TipTapBundle) {
		console.error('TipTapBundle ausente — gere o bundle (documentos/frontend/README.md).')
		return
	}
	const { Extension } = window.TipTapBundle

	const FontAttrs = Extension.create({
		name: 'fontAttrs',
		addGlobalAttributes() {
			return [{
				types: ['textStyle'],
				attributes: {
					fontFamily: {
						default: null,
						parseHTML: el => el.style.fontFamily || null,
						renderHTML: attrs => attrs.fontFamily ? { style: `font-family: ${attrs.fontFamily}` } : {},
					},
					fontSize: {
						default: null,
						parseHTML: el => el.style.fontSize || null,
						renderHTML: attrs => attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {},
					},
				},
			}]
		},
	})

	window.FontAttrsExtension = FontAttrs
})()
```

- [ ] **Step 4: Registrar o script e a extensão**

Em `documentos/templates/documentos/modelo_editor.html:191-195`, adicionar a linha do `font-attrs.js` entre `indent-attrs.js` e `ruler.js`:

```html
<script src="{% static 'documentos/js/vendor/tiptap.bundle.min.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/variavel-node.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/indent-attrs.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/font-attrs.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/ruler.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/editor-init.js' %}?v={{ asset_ver }}"></script>
```

Em `documentos/static/documentos/js/editor/editor-init.js:69-99`, dentro de `criarExtensoes(margensPx)`, adicionar `window.FontAttrsExtension,` logo após `window.IndentAttrsExtension,` (linha 82):

```js
			window.VariavelNode,
			window.IndentAttrsExtension,
			window.FontAttrsExtension,
			T.PaginationPlus.configure({
```

- [ ] **Step 5: Rodar `collectstatic` e o teste de novo**

Run:
```bash
python manage.py collectstatic --noinput
python -m pytest documentos/tests/test_editor_font_attrs.py -v
```
Expected: PASS (2 testes). Os testes chamam `window._editor.chain()...setMark(...)` diretamente via JS, sem depender de clique em botão de toolbar — por isso já passam aqui, antes dos dropdowns existirem (Steps 6-7 abaixo são sobre a UI, não sobre a extensão em si).

- [ ] **Step 6: Adicionar os dropdowns na toolbar**

Em `documentos/templates/documentos/modelo_editor.html`, dentro do `toolbar-group` que já tem o dropdown de cor (linhas 66-76), adicionar ANTES do dropdown de cor existente:

```html
						<div class="dropdown d-inline">
							<button type="button" class="btn btn-light btn-sm dropdown-toggle" data-bs-toggle="dropdown" title="Família da fonte">Fonte</button>
							<div class="dropdown-menu p-2">
								{% for valor, rotulo in fontes_familia %}
								<button type="button" class="dropdown-item" data-font-family="{{ valor }}" style="font-family: {{ valor }}">{{ rotulo }}</button>
								{% endfor %}
								<button type="button" class="btn btn-link btn-sm p-0 mt-2 text-decoration-none" data-action="font-family-clear">Remover fonte</button>
							</div>
						</div>
						<div class="dropdown d-inline">
							<button type="button" class="btn btn-light btn-sm dropdown-toggle" data-bs-toggle="dropdown" title="Tamanho da fonte">Tam.</button>
							<div class="dropdown-menu p-2">
								{% for tamanho in fontes_tamanho %}
								<button type="button" class="dropdown-item" data-font-size="{{ tamanho }}">{{ tamanho }}pt</button>
								{% endfor %}
								<button type="button" class="btn btn-link btn-sm p-0 mt-2 text-decoration-none" data-action="font-size-clear">Remover tamanho</button>
							</div>
						</div>
```

- [ ] **Step 7: Wiring dos dropdowns e dos botões "Remover"**

Em `documentos/static/documentos/js/editor/editor-init.js`, adicionar logo após o bloco `[data-highlight]` (depois da linha 348):

```js
	// ---- Família da fonte (lista fixa) ----
	document.querySelectorAll('[data-font-family]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().setMark('textStyle', { fontFamily: btn.dataset.fontFamily }).run()
		})
	})

	// ---- Tamanho da fonte (lista fixa, em pt) ----
	document.querySelectorAll('[data-font-size]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().setMark('textStyle', { fontSize: `${btn.dataset.fontSize}pt` }).run()
		})
	})
```

No `switch (acao)` dentro do handler `[data-action]` (dentro do bloco que começa na linha 279), adicionar dois `case` novos logo após `case 'highlight-clear': chain.unsetHighlight().run(); break` (linha 311):

```js
				case 'highlight-clear': chain.unsetHighlight().run(); break
				case 'font-family-clear': chain.setMark('textStyle', { fontFamily: null }).run(); break
				case 'font-size-clear': chain.setMark('textStyle', { fontSize: null }).run(); break
```

- [ ] **Step 8: Rodar `collectstatic` e confirmar os testes passam**

Run:
```bash
python manage.py collectstatic --noinput
python -m pytest documentos/tests/test_editor_font_attrs.py -v
```
Expected: PASS (2 testes)

- [ ] **Step 9: Rodar a suíte inteira do editor pra checar regressão**

Run: `python -m pytest documentos/tests/ -v`
Expected: mesmos resultados de antes desta task (as 2 falhas pré-existentes em `test_services.py`, sem nenhuma nova)

- [ ] **Step 10: Commit**

```bash
git add documentos/static/documentos/js/editor/font-attrs.js documentos/static/documentos/js/editor/editor-init.js \
        documentos/templates/documentos/modelo_editor.html documentos/tests/test_editor_font_attrs.py
git commit -m "feat(documentos): add font family/size toolbar controls via textStyle mark attrs"
```
