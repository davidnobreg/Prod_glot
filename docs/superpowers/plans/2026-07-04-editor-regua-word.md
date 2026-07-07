# Régua estilo Word no editor de modelos (TipTap) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar régua horizontal/vertical estilo Word ao editor de modelos (`documentos/modelos/<id>/`), com margem de página (persistida em `ConfiguracaoDocumento`, já lida pelos dois motores de PDF) e recuo de parágrafo (persistido inline no `conteudo_html`).

**Architecture:** Componente de régua vanilla JS (sem dependência nova), extensão TipTap de atributos de parágrafo para recuo, endpoint Django novo para persistir margem por empreendimento, e reinício controlado da instância `Editor` ao soltar o marcador de margem de página (a extensão `PaginationPlus` não expõe atualização de margem em runtime).

**Tech Stack:** Django (views finas + `services.py`), TipTap v3 (bundle vendorizado via esbuild, `documentos/frontend/entry.js`), JS vanilla (sem framework novo), pytest-django + pytest-playwright (padrão já usado em `clientes/tests/conftest.py`).

## Global Constraints

- TipTap v3 (`^3.0.0`); nenhum pacote npm novo nesta fase — recuo de parágrafo usa `Extension` (já disponível em `@tiptap/core`, só precisa ser exportado no bundle); régua é JS vanilla.
- Após qualquer rebuild do bundle (`npx esbuild ...`), rodar `python manage.py collectstatic --noinput` antes de testar — `STATIC_ROOT` não atualiza sozinho (causa raiz do bug investigado nesta sessão).
- Python: tabs, PEP 8. JS: sem ponto-e-vírgula desnecessário, `const`/`let`, camelCase.
- Views novas usam `@has_permission_decorator` já existente (`documentoConfig` para a rota de margem, `documentoModelos` já cobre o editor) — nenhuma permissão nova.
- URLs existentes não mudam; só adiciona novas, seguindo `path('recurso/<int:pk>/acao/', ...)`.
- Cada tarefa termina com commit próprio, sem push (aguardar autorização do usuário).

---

### Task 1: Persistir margem de página por empreendimento

**Files:**
- Modify: `documentos/services.py` (adicionar função no fim do arquivo)
- Modify: `documentos/views_documentos.py:1-27` (imports) e fim do arquivo (nova view)
- Modify: `documentos/urls.py`
- Test: `documentos/tests/test_views_margens.py` (novo)

**Interfaces:**
- Produces: `services.atualizar_margens_documento(empreendimento, margem_sup, margem_dir, margem_inf, margem_esq) -> list[str]` (lista de erros; vazia = sucesso, já salvou).
- Produces: URL reversível `documentos:empreendimento-margens-salvar` com `args=[empreendimento_id]`, aceita só `POST`, body JSON `{margem_sup, margem_dir, margem_inf, margem_esq}` (int, mm), retorna `{"ok": true}` ou `{"ok": false, "erros": [...]}`.

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/test_views_margens.py`:

```python
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento
from empreendimentos.models import Empreendimento

User = get_user_model()


def _make_empreendimento():
	return Empreendimento.objects.create(
		nome='Residencial Teste', telefone='(83) 99999-9999',
		tempo_reserva=30, quantidade_parcela=60,
	)


class EmpreendimentoMargensSalvarTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_margens_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.empr = _make_empreendimento()

	def test_salva_margens_validas_cria_configuracao(self):
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		resp = self.client.post(
			url,
			data=json.dumps({'margem_sup': 30, 'margem_dir': 25, 'margem_inf': 25, 'margem_esq': 35}),
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(resp.json()['ok'])
		cfg = ConfiguracaoDocumento.objects.get(empreendimento=self.empr)
		self.assertEqual(cfg.margem_sup, 30)
		self.assertEqual(cfg.margem_dir, 25)
		self.assertEqual(cfg.margem_inf, 25)
		self.assertEqual(cfg.margem_esq, 35)

	def test_atualiza_configuracao_existente(self):
		ConfiguracaoDocumento.objects.create(empreendimento=self.empr)
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		self.client.post(
			url,
			data=json.dumps({'margem_sup': 40, 'margem_dir': 20, 'margem_inf': 20, 'margem_esq': 30}),
			content_type='application/json',
		)
		self.assertEqual(ConfiguracaoDocumento.objects.filter(empreendimento=self.empr).count(), 1)
		cfg = ConfiguracaoDocumento.objects.get(empreendimento=self.empr)
		self.assertEqual(cfg.margem_sup, 40)

	def test_rejeita_margem_fora_do_intervalo(self):
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		resp = self.client.post(
			url,
			data=json.dumps({'margem_sup': 200, 'margem_dir': 25, 'margem_inf': 25, 'margem_esq': 35}),
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 400)
		self.assertFalse(resp.json()['ok'])
		self.assertFalse(ConfiguracaoDocumento.objects.filter(empreendimento=self.empr).exists())

	def test_get_nao_permitido(self):
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 405)
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python manage.py test documentos.tests.test_views_margens -v 2`
Expected: FAIL (`NoReverseMatch: 'empreendimento-margens-salvar' is not a valid view function or pattern name`)

- [ ] **Step 3: Implementar o service**

Adicionar ao fim de `documentos/services.py`:

```python
# ----------------------------------------------------------
# Margem de página por empreendimento (régua do editor)
# ----------------------------------------------------------
def atualizar_margens_documento(empreendimento, margem_sup, margem_dir, margem_inf, margem_esq):
	"""Atualiza (ou cria) a ConfiguracaoDocumento do empreendimento com novas
	margens de página, em mm. Retorna lista de erros; vazia = salvou OK."""
	from .models import ConfiguracaoDocumento

	valores = {
		'margem_sup': margem_sup, 'margem_dir': margem_dir,
		'margem_inf': margem_inf, 'margem_esq': margem_esq,
	}
	erros = []
	for nome, valor in valores.items():
		if not isinstance(valor, int) or isinstance(valor, bool) or valor < 5 or valor > 100:
			erros.append(f'{nome} deve ser um inteiro entre 5 e 100 (mm).')
	if erros:
		return erros

	cfg, _ = ConfiguracaoDocumento.objects.get_or_create(empreendimento=empreendimento)
	cfg.margem_sup = margem_sup
	cfg.margem_dir = margem_dir
	cfg.margem_inf = margem_inf
	cfg.margem_esq = margem_esq
	cfg.save(update_fields=['margem_sup', 'margem_dir', 'margem_inf', 'margem_esq'])
	return []
```

- [ ] **Step 4: Implementar a view**

Em `documentos/views_documentos.py`, adicionar o import de `Empreendimento` no topo (perto de `from vendas.models import RegisterVenda`):

```python
from empreendimentos.models import Empreendimento
```

E adicionar a view no fim do arquivo:

```python
@has_permission_decorator('documentoConfig')
def empreendimento_margens_salvar(request, empreendimento_id):
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'erros': ['Método inválido']}, status=405)
	empreendimento = get_object_or_404(Empreendimento, pk=empreendimento_id)
	try:
		dados = json.loads(request.body)
	except json.JSONDecodeError:
		return JsonResponse({'ok': False, 'erros': ['JSON inválido']}, status=400)

	campos = ('margem_sup', 'margem_dir', 'margem_inf', 'margem_esq')
	if any(campo not in dados for campo in campos):
		return JsonResponse({'ok': False, 'erros': ['Campos de margem ausentes']}, status=400)

	erros = services.atualizar_margens_documento(
		empreendimento,
		margem_sup=dados['margem_sup'],
		margem_dir=dados['margem_dir'],
		margem_inf=dados['margem_inf'],
		margem_esq=dados['margem_esq'],
	)
	if erros:
		return JsonResponse({'ok': False, 'erros': erros}, status=400)
	return JsonResponse({'ok': True})
```

- [ ] **Step 5: Registrar a URL**

Em `documentos/urls.py`, adicionar ao import de `views_documentos`:

```python
from .views_documentos import (
    modelos_lista,
    modelo_editor,
    modelo_salvar,
    modelo_preview,
    modelo_duplicar,
    modelo_toggle_ativo,
    modelo_historico,
    variaveis_lista,
    empreendimento_margens_salvar,
)
```

E adicionar ao `urlpatterns`, logo após a linha de `modelo-toggle-ativo`:

```python
    path('empreendimentos/<int:empreendimento_id>/margens/', empreendimento_margens_salvar, name='empreendimento-margens-salvar'),
```

- [ ] **Step 6: Rodar o teste e confirmar que passa**

Run: `python manage.py test documentos.tests.test_views_margens -v 2`
Expected: PASS (4 testes)

- [ ] **Step 7: Commit**

```bash
git add documentos/services.py documentos/views_documentos.py documentos/urls.py documentos/tests/test_views_margens.py
git commit -m "feat(documentos): add endpoint to persist per-empreendimento page margins"
```

---

### Task 2: Contexto do editor — empreendimentos vinculados ao modelo

**Files:**
- Modify: `documentos/views_documentos.py:83-105` (view `modelo_editor`)
- Modify: `documentos/templates/documentos/modelo_editor.html:9-35` (dropdown na topbar) e `:166-173` (`EDITOR_CONFIG`)
- Test: `documentos/tests/test_views_modelo_editor_context.py` (novo)

**Interfaces:**
- Consumes: `EmpreendimentoDocumento` (model, `empreendimento` FK, `modelo` FK, `ativo`), `ConfiguracaoDocumento.margem_sup/dir/inf/esq` (Task 1).
- Produces: contexto `empreendimentos_vinculo` (lista de dicts `{id, nome, margem_sup, margem_dir, margem_inf, margem_esq}`) e `empreendimentos_json` (mesma lista serializada) disponíveis no template `modelo_editor.html`; `window.EDITOR_CONFIG.empreendimentos` no JS.

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/test_views_modelo_editor_context.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento

User = get_user_model()


class ModeloEditorEmpreendimentosContextTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_ctx_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.empr = Empreendimento.objects.create(
			nome='Loteamento Régua Teste', telefone='(83) 98888-8888',
			tempo_reserva=30, quantidade_parcela=60,
		)
		ConfiguracaoDocumento.objects.create(empreendimento=self.empr, margem_sup=33, margem_dir=22, margem_inf=22, margem_esq=44)
		self.modelo = ModeloDocumento.objects.create(
			titulo='Contrato Régua Teste', tipo=TipoDocumento.CONTRATO,
			conteudo_html='<p>Teste</p>', criado_por=self.user,
		)
		EmpreendimentoDocumento.objects.create(empreendimento=self.empr, modelo=self.modelo)

	def test_editor_lista_empreendimento_vinculado_com_margens(self):
		url = reverse('documentos:modelo-editor', args=[self.modelo.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'Loteamento Régua Teste')
		self.assertContains(resp, str(self.empr.pk))
		self.assertContains(resp, '33')
		self.assertContains(resp, '44')

	def test_editor_sem_vinculo_lista_vazia(self):
		modelo_sem_vinculo = ModeloDocumento.objects.create(
			titulo='Proposta Sem Vínculo', tipo=TipoDocumento.PROPOSTA,
			conteudo_html='<p>x</p>', criado_por=self.user,
		)
		url = reverse('documentos:modelo-editor', args=[modelo_sem_vinculo.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.context['empreendimentos_vinculo'], [])
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python manage.py test documentos.tests.test_views_modelo_editor_context -v 2`
Expected: FAIL (`KeyError: 'empreendimentos_vinculo'` no `resp.context`)

- [ ] **Step 3: Implementar no view**

Substituir a função `modelo_editor` em `documentos/views_documentos.py:83-105` por:

```python
@has_permission_decorator('documentoModelos')
def modelo_editor(request, pk=None):
	modelo = get_object_or_404(ModeloDocumento, pk=pk) if pk else None
	salvar_url = reverse('documentos:modelo-salvar', args=[pk]) if pk else reverse('documentos:modelo-salvar-novo')
	conteudo = modelo.conteudo_html if modelo else ''

	empreendimentos_vinculo = []
	if modelo:
		vinculos = EmpreendimentoDocumento.objects.filter(
			modelo=modelo, ativo=True,
		).select_related('empreendimento', 'empreendimento__config_documento')
		for v in vinculos:
			cfg = getattr(v.empreendimento, 'config_documento', None)
			empreendimentos_vinculo.append({
				'id': v.empreendimento_id,
				'nome': v.empreendimento.nome,
				'margem_sup': cfg.margem_sup if cfg else 25,
				'margem_dir': cfg.margem_dir if cfg else 20,
				'margem_inf': cfg.margem_inf if cfg else 20,
				'margem_esq': cfg.margem_esq if cfg else 30,
			})

	return render(request, 'documentos/modelo_editor.html', {
		'modelo': modelo,
		'tipos': TipoDocumento.choices,
		'variaveis_por_categoria': _variaveis_por_categoria(),
		'variaveis_json': json.dumps(list(
			VariavelDocumento.objects.filter(ativo=True).values('tag_slug', 'label', 'categoria')
		)),
		'salvar_url': salvar_url,
		'conteudo_inicial_json': json.dumps(conteudo),
		'asset_ver': str(_asset_ver()),
		'empreendimentos_vinculo': empreendimentos_vinculo,
		'empreendimentos_json': json.dumps(empreendimentos_vinculo),
		'cores_texto': [
			'#000000', '#dc3545', '#fd7e14', '#ffc107',
			'#198754', '#0d6efd', '#6f42c1', '#6c757d',
		],
		'cores_realce': [
			'#fff3cd', '#d1e7dd', '#cfe2ff', '#f8d7da',
			'#e2e3e5', '#ffe5b4', '#d3f9d8', '#e5dbff',
		],
	})
```

Nota: `select_related('empreendimento__config_documento')` funciona porque `config_documento` é `OneToOneField` (related_name reverso funciona com `select_related` normalmente).

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python manage.py test documentos.tests.test_views_modelo_editor_context -v 2`
Expected: PASS (2 testes)

- [ ] **Step 5: Adicionar dropdown no template**

Em `documentos/templates/documentos/modelo_editor.html`, dentro do `<div class="card-body d-flex flex-wrap gap-2 align-items-end">` (linha 13), adicionar um novo bloco logo após o `<div>` do Tipo (linha 26, antes do `<div class="d-flex gap-2">` de Voltar/Salvar):

```html
			<div>
				<label class="form-label small text-muted">Empreendimento (margem)</label>
				<select id="modeloEmpreendimento" class="form-select form-select-sm">
					<option value="">Padrão ABNT (somente leitura)</option>
					{% for e in empreendimentos_vinculo %}
						<option value="{{ e.id }}">{{ e.nome }}</option>
					{% endfor %}
				</select>
			</div>
```

- [ ] **Step 6: Expor no `EDITOR_CONFIG`**

Em `documentos/templates/documentos/modelo_editor.html:166-173`, alterar:

```html
<script>
	window.EDITOR_CONFIG = {
		csrf: '{{ csrf_token }}',
		salvarUrl: '{{ salvar_url }}',
		conteudoInicial: {{ conteudo_inicial_json|safe }},
		empreendimentos: {{ empreendimentos_json|safe }},
	}
</script>
```

- [ ] **Step 7: Commit**

```bash
git add documentos/views_documentos.py documentos/templates/documentos/modelo_editor.html documentos/tests/test_views_modelo_editor_context.py
git commit -m "feat(documentos): expose linked empreendimentos and their margins to the modelo editor"
```

---

### Task 3: Extensão de recuo de parágrafo no bundle TipTap

**Files:**
- Modify: `documentos/frontend/entry.js`
- Create: `documentos/static/documentos/js/editor/indent-attrs.js`
- Modify: `documentos/templates/documentos/modelo_editor.html:174-176` (scripts)
- Modify: `documentos/static/documentos/js/editor/editor-init.js:55-82` (extensions array)
- Modify: `documentos/frontend/README.md` (nota da extensão nova)
- Test: `documentos/tests/conftest.py` (novo, fixtures de browser) e `documentos/tests/test_editor_indent.py` (novo)

**Interfaces:**
- Produces: `window.TipTapBundle.Extension` (classe `Extension` de `@tiptap/core`, antes ausente do bundle).
- Produces: `window.IndentAttrsExtension` — extensão TipTap que adiciona `indentLeft`, `indentRight`, `indentFirstLine` (px, `indentFirstLine` pode ser negativo = recuo deslocado/hanging) ao nó `paragraph`, serializados como `margin-left`/`margin-right`/`text-indent` inline no HTML salvo.
- Consumes (Task futura): parágrafo aceita `editor.chain().updateAttributes('paragraph', {indentLeft, indentRight, indentFirstLine}).run()`.

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/conftest.py` (fixtures de browser logado, mesmo padrão de `clientes/tests/conftest.py`):

```python
import os

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')

User = get_user_model()

_LOGIN_EMAIL = 'admin_documentos@glot.test'
_LOGIN_PASS = 'glotpass123'


@pytest.fixture(scope='session', autouse=True)
def suppress_post_migrate_glot_permissions():
	from accounts.apps import create_glot_permissions
	from django.apps import apps as django_apps
	from django.db.models.signals import post_migrate
	accounts_config = django_apps.get_app_config('accounts')
	post_migrate.disconnect(create_glot_permissions, sender=accounts_config)
	yield
	post_migrate.connect(create_glot_permissions, sender=accounts_config)


@pytest.fixture
def superuser(transactional_db):
	user = User(
		username=_LOGIN_EMAIL,
		email=_LOGIN_EMAIL,
		first_name='Admin',
		last_name='Documentos',
		tipo_usuario='ADMINISTRADOR',
		contato='(83) 99999-9999',
		is_superuser=True,
		is_staff=True,
		is_active=True,
	)
	user.password = make_password(_LOGIN_PASS)
	User.objects.bulk_create([user])
	return User.objects.get(username=_LOGIN_EMAIL)


@pytest.fixture
def logged_browser(page, live_server, superuser):
	page.goto(f'{live_server.url}/')
	page.fill('input[name="email"]', _LOGIN_EMAIL)
	page.fill('input[name="senha"]', _LOGIN_PASS)
	page.click('button[type="submit"]')
	page.wait_for_load_state('networkidle')
	return page
```

Criar `documentos/tests/test_editor_indent.py`:

```python
import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Indent Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Parágrafo de teste para recuo.</p>',
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_paragrafo_aceita_e_persiste_atributos_de_recuo(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	html_antes = page.evaluate('window._editor.getHTML()')
	assert 'Parágrafo de teste' in html_antes

	page.evaluate('''
		() => {
			window._editor.chain().focus().updateAttributes('paragraph', {
				indentLeft: 40, indentRight: 20, indentFirstLine: -20,
			}).run()
		}
	''')
	html_depois = page.evaluate('window._editor.getHTML()')
	assert 'margin-left: 40px' in html_depois
	assert 'margin-right: 20px' in html_depois
	assert 'text-indent: -20px' in html_depois
	assert 'Parágrafo de teste' in html_depois
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest documentos/tests/test_editor_indent.py -v`
Expected: FAIL (`TypeError: editor.chain(...).updateAttributes is not a function` ou atributo não reconhecido — `indentAttrs` ainda não existe)

- [ ] **Step 3: Exportar `Extension` no bundle**

Em `documentos/frontend/entry.js`, alterar a linha 5 e a exportação final:

```js
import { Editor, Node, Extension, mergeAttributes } from '@tiptap/core'
```

```js
window.TipTapBundle = {
  Editor, Node, Extension, mergeAttributes, StarterKit,
  TextAlign, Table, TableRow, TableCell, TableHeader,
  TextStyle, Color, Highlight, Subscript, Superscript,
  PaginationPlus, CharacterCount,
}
```

- [ ] **Step 4: Criar a extensão de atributos de recuo**

Criar `documentos/static/documentos/js/editor/indent-attrs.js`:

```js
// Extensão IndentAttrs — adiciona recuo (esquerdo/direito/primeira linha) ao
// nó "paragraph" do StarterKit sem redeclarar o nó (evita "Duplicate
// extension names"). indentFirstLine negativo = recuo deslocado (hanging).
(function () {
	if (!window.TipTapBundle) {
		console.error('TipTapBundle ausente — gere o bundle (documentos/frontend/README.md).')
		return
	}
	const { Extension } = window.TipTapBundle

	const IndentAttrs = Extension.create({
		name: 'indentAttrs',
		addGlobalAttributes() {
			return [{
				types: ['paragraph'],
				attributes: {
					indentLeft: {
						default: 0,
						parseHTML: el => parseInt(el.style.marginLeft, 10) || 0,
						renderHTML: attrs => attrs.indentLeft ? { style: `margin-left: ${attrs.indentLeft}px` } : {},
					},
					indentRight: {
						default: 0,
						parseHTML: el => parseInt(el.style.marginRight, 10) || 0,
						renderHTML: attrs => attrs.indentRight ? { style: `margin-right: ${attrs.indentRight}px` } : {},
					},
					indentFirstLine: {
						default: 0,
						parseHTML: el => parseInt(el.style.textIndent, 10) || 0,
						renderHTML: attrs => attrs.indentFirstLine ? { style: `text-indent: ${attrs.indentFirstLine}px` } : {},
					},
				},
			}]
		},
	})

	window.IndentAttrsExtension = IndentAttrs
})()
```

- [ ] **Step 5: Rebuild do bundle e collectstatic**

Run:
```bash
cd documentos/frontend
npx esbuild entry.js --bundle --minify --format=iife --outfile=../static/documentos/js/vendor/tiptap.bundle.min.js
cd ../..
python manage.py collectstatic --noinput
```
Expected: bundle regenerado sem erro; `grep -c "indentAttrs\|IndentAttrs" documentos/static/documentos/js/vendor/tiptap.bundle.min.js` — não deve achar nada ainda (o `indent-attrs.js` é carregado à parte, não faz parte do `entry.js`); o que importa aqui é `Extension` estar presente: `grep -c "class Extension" documentos/static/documentos/js/vendor/tiptap.bundle.min.js` deve retornar >= 1.

- [ ] **Step 6: Adicionar o script novo e registrar a extensão**

Em `documentos/templates/documentos/modelo_editor.html:174-176`, adicionar a linha do `indent-attrs.js` entre `variavel-node.js` e `editor-init.js`:

```html
<script src="{% static 'documentos/js/vendor/tiptap.bundle.min.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/variavel-node.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/indent-attrs.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/editor-init.js' %}?v={{ asset_ver }}"></script>
```

Em `documentos/static/documentos/js/editor/editor-init.js:55-82`, adicionar `window.IndentAttrsExtension,` à lista de `extensions`, logo após `window.VariavelNode,`:

```js
		extensions: [
			T.StarterKit.configure({ link: { openOnClick: false, autolink: true } }),
			T.TextAlign.configure({ types: ['heading', 'paragraph'] }),
			T.Table.configure({ resizable: true }),
			T.TableRow, T.TableHeader, T.TableCell,
			T.TextStyle,
			T.Color,
			T.Highlight.configure({ multicolor: true }),
			T.Subscript,
			T.Superscript,
			T.CharacterCount,
			window.VariavelNode,
			window.IndentAttrsExtension,
			T.PaginationPlus.configure({
```

- [ ] **Step 7: Rodar o teste e confirmar que passa**

Run: `python -m pytest documentos/tests/test_editor_indent.py -v`
Expected: PASS

- [ ] **Step 8: Atualizar o README do bundle**

Em `documentos/frontend/README.md`, adicionar uma seção curta (seguindo o padrão da seção "Paginação visual (PaginationPlus)" já existente):

```markdown
## Recuo de parágrafo (IndentAttrs)

Desde a Fase A da régua, `entry.js` exporta `Extension` (de `@tiptap/core`)
além dos nós/marcas de sempre. `documentos/static/documentos/js/editor/indent-attrs.js`
usa esse `Extension` pra declarar `indentLeft`, `indentRight` e `indentFirstLine`
no nó `paragraph`, sem precisar redeclarar o nó inteiro (evita "Duplicate
extension names"). Serializa como `margin-left`/`margin-right`/`text-indent`
inline no HTML salvo — mesmo mecanismo de round-trip de negrito/cor/etc.
```

- [ ] **Step 9: Commit**

```bash
git add documentos/frontend/entry.js documentos/frontend/README.md documentos/frontend/package-lock.json \
        documentos/static/documentos/js/vendor/tiptap.bundle.min.js \
        documentos/static/documentos/js/editor/indent-attrs.js documentos/static/documentos/js/editor/editor-init.js \
        documentos/templates/documentos/modelo_editor.html \
        documentos/tests/conftest.py documentos/tests/test_editor_indent.py
git commit -m "feat(documentos): add paragraph indent attributes extension to TipTap bundle"
```

---

### Task 4: Régua estática (renderização, sem arrastar ainda)

**Files:**
- Create: `documentos/static/documentos/js/editor/ruler.js`
- Modify: `documentos/templates/documentos/modelo_editor.html:131-137` (slots da régua) e bloco `<style>` (:178-202)
- Modify: `documentos/static/documentos/js/editor/editor-init.js` (inicializar a régua com as margens do primeiro empreendimento vinculado, ou ABNT padrão)
- Test: `documentos/tests/test_editor_ruler.py` (novo)

**Interfaces:**
- Produces: `window.DocRuler.init({ horizContainer, vertContainer, pageWidthPx, pageHeightPx, margensPx: {top,right,bottom,left} }) -> { horizEl, vertEl, getMargens(), setMargens(novasMargensPx) }`.
- Produces: `window.DocRuler.MM_TO_PX` (substitui a constante local duplicada em `editor-init.js`).
- Consumes (Task 5/6): `setMargens` será chamado durante o drag; a interação em si vem nas próximas tasks.

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/test_editor_ruler.py`:

```python
import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def modelo_com_empreendimento(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento Ruler Teste', telefone='(83) 97777-7777',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=30, margem_dir=25, margem_inf=25, margem_esq=35)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Ruler Teste', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto de teste.</p>', criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo


@pytest.mark.django_db
def test_regua_renderiza_com_zonas_de_margem(logged_browser, live_server, modelo_com_empreendimento):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_empreendimento.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')
	page.wait_for_selector('.doc-ruler-vertical')

	largura_esq = page.eval_on_selector('.doc-ruler-margem-esquerda', 'el => el.style.width')
	assert largura_esq != ''

	# 35mm * (96/25.4) ~= 132.28px -> arredondado
	largura_px = float(largura_esq.replace('px', ''))
	assert 125 < largura_px < 140
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest documentos/tests/test_editor_ruler.py -v`
Expected: FAIL (`TimeoutError` esperando `.doc-ruler-horizontal` — régua ainda não existe)

- [ ] **Step 3: Criar o componente de régua**

Criar `documentos/static/documentos/js/editor/ruler.js`:

```js
// Régua horizontal/vertical estilo Word — zonas de margem de página (cinza)
// e ticks em polegada. Renderização estática nesta fase; drag vem depois.
(function () {
	const MM_TO_PX = 96 / 25.4
	const PX_PER_INCH = 96

	function criarTicks(comprimentoPx) {
		const frag = document.createDocumentFragment()
		let posPx = 0
		let polegada = 0
		while (posPx < comprimentoPx) {
			const tick = document.createElement('div')
			tick.className = 'doc-ruler-tick'
			tick.style.left = `${posPx}px`
			tick.textContent = polegada > 0 ? `${polegada}"` : ''
			frag.appendChild(tick)
			posPx += PX_PER_INCH
			polegada += 1
		}
		return frag
	}

	function criarZonaMargem(ladoClasse) {
		const zona = document.createElement('div')
		zona.className = `doc-ruler-margem doc-ruler-margem-${ladoClasse}`
		return zona
	}

	function init(options) {
		const { horizContainer, vertContainer, pageWidthPx, pageHeightPx } = options
		let margens = { ...options.margensPx }

		const horiz = document.createElement('div')
		horiz.className = 'doc-ruler doc-ruler-horizontal'
		horiz.style.width = `${pageWidthPx}px`

		const vert = document.createElement('div')
		vert.className = 'doc-ruler doc-ruler-vertical'
		vert.style.height = `${pageHeightPx}px`

		const zonaEsq = criarZonaMargem('esquerda')
		const zonaDir = criarZonaMargem('direita')
		const zonaSup = criarZonaMargem('superior')
		const zonaInf = criarZonaMargem('inferior')

		horiz.appendChild(criarTicks(pageWidthPx))
		horiz.appendChild(zonaEsq)
		horiz.appendChild(zonaDir)
		vert.appendChild(zonaSup)
		vert.appendChild(zonaInf)

		function repintar() {
			zonaEsq.style.left = '0px'
			zonaEsq.style.width = `${margens.left}px`
			zonaDir.style.right = '0px'
			zonaDir.style.width = `${margens.right}px`
			zonaSup.style.top = '0px'
			zonaSup.style.height = `${margens.top}px`
			zonaInf.style.bottom = '0px'
			zonaInf.style.height = `${margens.bottom}px`
		}
		repintar()

		horizContainer.appendChild(horiz)
		vertContainer.appendChild(vert)

		return {
			horizEl: horiz,
			vertEl: vert,
			getMargens: () => ({ ...margens }),
			setMargens(novasMargensPx) {
				margens = { ...margens, ...novasMargensPx }
				repintar()
			},
		}
	}

	window.DocRuler = { init, MM_TO_PX, PX_PER_INCH }
})()
```

- [ ] **Step 4: Adicionar os slots no template e CSS**

Em `documentos/templates/documentos/modelo_editor.html:131-137`, substituir:

```html
			<div class="card shadow-sm">
				<div class="card-body" style="background:#e9ecef;overflow:auto;max-height:78vh;">
					<div class="editor-a4-shell">
						<div id="tiptapEditor"></div>
					</div>
				</div>
			</div>
```

por:

```html
			<div class="card shadow-sm">
				<div class="card-body" style="background:#e9ecef;overflow:auto;max-height:78vh;">
					<div style="display:flex;">
						<div id="rulerVerticalSlot"></div>
						<div style="flex:1;">
							<div id="rulerHorizontalSlot"></div>
							<div class="editor-a4-shell">
								<div id="tiptapEditor"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
```

No bloco `<style>` do mesmo arquivo (linhas 178-202), adicionar antes do `</style>`:

```css
	.doc-ruler { position: sticky; background: #f8f9fa; border: 1px solid #adb5bd; flex-shrink: 0; z-index: 5; }
	.doc-ruler-horizontal { height: 24px; margin-left: 24px; top: 0; }
	.doc-ruler-vertical { width: 24px; left: 0; }
	.doc-ruler-tick { position: absolute; top: 0; height: 100%; border-left: 1px solid #adb5bd; font-size: 9px; color: #6c757d; padding-left: 2px; }
	.doc-ruler-margem { position: absolute; background: #ced4da; }
	.doc-ruler-margem-esquerda, .doc-ruler-margem-direita { top: 0; height: 100%; }
	.doc-ruler-margem-superior, .doc-ruler-margem-inferior { left: 0; width: 100%; }
```

- [ ] **Step 5: Carregar `ruler.js` e inicializar no `editor-init.js`**

Em `documentos/templates/documentos/modelo_editor.html`, adicionar o script antes de `editor-init.js`:

```html
<script src="{% static 'documentos/js/editor/ruler.js' %}?v={{ asset_ver }}"></script>
<script src="{% static 'documentos/js/editor/editor-init.js' %}?v={{ asset_ver }}"></script>
```

Em `documentos/static/documentos/js/editor/editor-init.js`, remover a constante local `MM_TO_PX` (linha 21) e usar `window.DocRuler.MM_TO_PX` no lugar; logo após a criação do `editor` (depois da linha `window._editor = editor`), inicializar a régua:

```js
	const MM_TO_PX = window.DocRuler.MM_TO_PX

	// ---- Régua (margem de página) ----
	const empreendimentos = cfg.empreendimentos || []
	const margensIniciais = empreendimentos.length
		? {
			top: Math.round(empreendimentos[0].margem_sup * MM_TO_PX),
			right: Math.round(empreendimentos[0].margem_dir * MM_TO_PX),
			bottom: Math.round(empreendimentos[0].margem_inf * MM_TO_PX),
			left: Math.round(empreendimentos[0].margem_esq * MM_TO_PX),
		}
		: { top: 94, right: 76, bottom: 76, left: 113 } // ABNT 25/20/20/30mm

	const ruler = window.DocRuler.init({
		horizContainer: document.getElementById('rulerHorizontalSlot'),
		vertContainer: document.getElementById('rulerVerticalSlot'),
		pageWidthPx: 794,
		pageHeightPx: 1123,
		margensPx: margensIniciais,
	})
```

(A referência a `MM_TO_PX` já usada mais abaixo, na configuração do `PaginationPlus`, continua funcionando sem alteração — só a origem da constante mudou.)

- [ ] **Step 6: Rebuild não é necessário nesta task**

`ruler.js` é carregado à parte do bundle esbuild (mesmo padrão de `variavel-node.js`), então não precisa rebuild nem collectstatic de `tiptap.bundle.min.js` — só collectstatic pra publicar o arquivo novo:

Run: `python manage.py collectstatic --noinput`

- [ ] **Step 7: Rodar o teste e confirmar que passa**

Run: `python -m pytest documentos/tests/test_editor_ruler.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add documentos/static/documentos/js/editor/ruler.js documentos/static/documentos/js/editor/editor-init.js \
        documentos/templates/documentos/modelo_editor.html documentos/tests/test_editor_ruler.py
git commit -m "feat(documentos): render static page-margin ruler in the modelo editor"
```

---

### Task 5: Arrastar margem de página (drag + reinício do editor + persistência)

**Files:**
- Modify: `documentos/static/documentos/js/editor/ruler.js` (marcadores arrastáveis + eventos)
- Modify: `documentos/static/documentos/js/editor/editor-init.js` (reinício do editor + fetch de persistência)
- Test: `documentos/tests/test_editor_ruler_drag.py` (novo)

**Interfaces:**
- Consumes: `ruler.setMargens` (Task 4).
- Produces: `ruler.onDrop(callback)` — `callback` recebe `{ top, right, bottom, left }` em px, chamado só no `mouseup` (drop), nunca durante o arraste.
- Produces (editor-init.js): função local `reiniciarEditorComNovaMargem(margensPx)` que destrói e recria `window._editor`, preservando conteúdo e seleção.

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/test_editor_ruler_drag.py`:

```python
import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def modelo_com_empreendimento(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento Drag Teste', telefone='(83) 96666-6666',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=25, margem_dir=20, margem_inf=20, margem_esq=30)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Drag Teste', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto original que não pode sumir.</p>', criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo, empr


@pytest.mark.django_db
def test_arrastar_marcador_de_margem_persiste_e_preserva_texto(logged_browser, live_server, modelo_com_empreendimento):
	modelo, empr = modelo_com_empreendimento
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')
	page.select_option('#modeloEmpreendimento', str(empr.pk))

	marcador = page.locator('.doc-ruler-marcador-margem-esquerda')
	box = marcador.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()

	page.wait_for_timeout(500)  # fetch de persistência é assíncrono

	texto_atual = page.evaluate('window._editor.getHTML()')
	assert 'Texto original que não pode sumir' in texto_atual

	empr.refresh_from_db()
	cfg = ConfiguracaoDocumento.objects.get(empreendimento=empr)
	assert cfg.margem_esq != 30

	# Reinício do editor não pode deixar um autosave "fantasma": deve ter
	# rodado iniciarAutosave() exatamente duas vezes (carga inicial + 1 drop),
	# não mais que isso (senão o setInterval antigo não foi limpo no destroy).
	contagem_autosave = page.evaluate('window.__autosaveInitCount')
	assert contagem_autosave == 2
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest documentos/tests/test_editor_ruler_drag.py -v`
Expected: FAIL (`.doc-ruler-marcador-margem-esquerda` não existe / `page.select_option` falha se `#modeloEmpreendimento` estiver sem essa opção selecionável travando drag — nesta fase o marcador ainda não é arrastável)

- [ ] **Step 3: Adicionar marcadores arrastáveis ao `ruler.js`**

Em `documentos/static/documentos/js/editor/ruler.js`, adicionar a função de marcador e o wiring de drag. Substituir a função `init` inteira por:

```js
	function criarMarcador(tipo, cursor) {
		const marcador = document.createElement('div')
		marcador.className = `doc-ruler-marcador doc-ruler-marcador-${tipo}`
		marcador.style.cursor = cursor
		return marcador
	}

	function init(options) {
		const { horizContainer, vertContainer, pageWidthPx, pageHeightPx } = options
		let margens = { ...options.margensPx }
		let readOnly = !!options.readOnly
		let onDropCb = null

		const horiz = document.createElement('div')
		horiz.className = 'doc-ruler doc-ruler-horizontal'
		horiz.style.width = `${pageWidthPx}px`

		const vert = document.createElement('div')
		vert.className = 'doc-ruler doc-ruler-vertical'
		vert.style.height = `${pageHeightPx}px`

		const zonaEsq = criarZonaMargem('esquerda')
		const zonaDir = criarZonaMargem('direita')
		const zonaSup = criarZonaMargem('superior')
		const zonaInf = criarZonaMargem('inferior')

		const marcadorEsq = criarMarcador('margem-esquerda', 'ew-resize')
		const marcadorDir = criarMarcador('margem-direita', 'ew-resize')
		const marcadorSup = criarMarcador('margem-superior', 'ns-resize')
		const marcadorInf = criarMarcador('margem-inferior', 'ns-resize')

		horiz.appendChild(criarTicks(pageWidthPx))
		horiz.appendChild(zonaEsq)
		horiz.appendChild(zonaDir)
		horiz.appendChild(marcadorEsq)
		horiz.appendChild(marcadorDir)
		vert.appendChild(zonaSup)
		vert.appendChild(zonaInf)
		vert.appendChild(marcadorSup)
		vert.appendChild(marcadorInf)

		function repintar() {
			zonaEsq.style.left = '0px'
			zonaEsq.style.width = `${margens.left}px`
			marcadorEsq.style.left = `${margens.left}px`

			zonaDir.style.right = '0px'
			zonaDir.style.width = `${margens.right}px`
			marcadorDir.style.left = `${pageWidthPx - margens.right}px`

			zonaSup.style.top = '0px'
			zonaSup.style.height = `${margens.top}px`
			marcadorSup.style.top = `${margens.top}px`

			zonaInf.style.bottom = '0px'
			zonaInf.style.height = `${margens.bottom}px`
			marcadorInf.style.top = `${pageHeightPx - margens.bottom}px`
		}
		repintar()

		function arrastarHorizontal(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				if (readOnly) { return }
				e.preventDefault()
				function onMove(ev) {
					const rect = horiz.getBoundingClientRect()
					const x = Math.max(0, Math.min(pageWidthPx, ev.clientX - rect.left))
					aplicar(x)
					repintar()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onDropCb) { onDropCb({ ...margens }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		function arrastarVertical(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				if (readOnly) { return }
				e.preventDefault()
				function onMove(ev) {
					const rect = vert.getBoundingClientRect()
					const y = Math.max(0, Math.min(pageHeightPx, ev.clientY - rect.top))
					aplicar(y)
					repintar()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onDropCb) { onDropCb({ ...margens }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		arrastarHorizontal(marcadorEsq, x => { margens.left = Math.round(x) })
		arrastarHorizontal(marcadorDir, x => { margens.right = Math.round(pageWidthPx - x) })
		arrastarVertical(marcadorSup, y => { margens.top = Math.round(y) })
		arrastarVertical(marcadorInf, y => { margens.bottom = Math.round(pageHeightPx - y) })

		horizContainer.appendChild(horiz)
		vertContainer.appendChild(vert)

		return {
			horizEl: horiz,
			vertEl: vert,
			getMargens: () => ({ ...margens }),
			setMargens(novasMargensPx) {
				margens = { ...margens, ...novasMargensPx }
				repintar()
			},
			setReadOnly(valor) { readOnly = valor },
			onDrop(callback) { onDropCb = callback },
		}
	}
```

Adicionar CSS do marcador no bloco `<style>` do template (junto do resto da régua, Task 4):

```css
	.doc-ruler-marcador { position: absolute; width: 8px; height: 8px; background: #495057; transform: translateX(-50%); }
	.doc-ruler-horizontal .doc-ruler-marcador { top: 0; height: 100%; }
	.doc-ruler-vertical .doc-ruler-marcador { left: 0; width: 100%; transform: translateY(-50%); }
```

- [ ] **Step 4: Reinício do editor + persistência em `editor-init.js`**

Logo após a inicialização do `ruler` (Task 4, Step 5), adicionar:

```js
	// ---- Dropdown de empreendimento: liga/desliga edição de margem ----
	const selectEmpreendimento = document.getElementById('modeloEmpreendimento')
	function empreendimentoSelecionado() {
		if (!selectEmpreendimento || !selectEmpreendimento.value) { return null }
		return empreendimentos.find(e => String(e.id) === selectEmpreendimento.value) || null
	}
	ruler.setReadOnly(!empreendimentoSelecionado())
	if (selectEmpreendimento) {
		selectEmpreendimento.addEventListener('change', () => {
			const emp = empreendimentoSelecionado()
			ruler.setReadOnly(!emp)
			if (emp) {
				ruler.setMargens({
					top: Math.round(emp.margem_sup * MM_TO_PX),
					right: Math.round(emp.margem_dir * MM_TO_PX),
					bottom: Math.round(emp.margem_inf * MM_TO_PX),
					left: Math.round(emp.margem_esq * MM_TO_PX),
				})
			}
		})
	}

	// ---- Drop do marcador de margem: reinicia o editor com nova paginação
	// e persiste no ConfiguracaoDocumento do empreendimento selecionado ----
	let autosaveIntervalId = null
	function iniciarAutosave(editorAtual) {
		window.__autosaveInitCount = (window.__autosaveInitCount || 0) + 1 // instrumentação de teste
		let sujoLocal = false
		editorAtual.on('update', () => { sujoLocal = true })
		autosaveIntervalId = setInterval(() => {
			if (sujoLocal) { sujoLocal = false; salvar() }
		}, 30000)
	}

	function reiniciarEditorComNovaMargem(margensPx) {
		const { from, to } = window._editor.state.selection
		const htmlAtual = window._editor.getHTML()
		if (autosaveIntervalId) { clearInterval(autosaveIntervalId) }
		window._editor.destroy()

		const novoEditor = new T.Editor({
			element: elEditor,
			editorProps: { transformPastedHTML: sanitizarHtmlColado },
			extensions: [
				T.StarterKit.configure({ link: { openOnClick: false, autolink: true } }),
				T.TextAlign.configure({ types: ['heading', 'paragraph'] }),
				T.Table.configure({ resizable: true }),
				T.TableRow, T.TableHeader, T.TableCell,
				T.TextStyle,
				T.Color,
				T.Highlight.configure({ multicolor: true }),
				T.Subscript,
				T.Superscript,
				T.CharacterCount,
				window.VariavelNode,
				window.IndentAttrsExtension,
				T.PaginationPlus.configure({
					pageWidth: 794,
					pageHeight: 1123,
					marginTop: margensPx.top,
					marginBottom: margensPx.bottom,
					marginLeft: margensPx.left,
					marginRight: margensPx.right,
					contentMarginTop: 0,
					contentMarginBottom: 0,
					pageGap: 30,
					footerLeft: '',
					footerRight: 'Página {page}',
					headerLeft: '',
					headerRight: '',
				}),
			],
			content: htmlAtual,
		})
		window._editor = novoEditor
		try { novoEditor.commands.setTextSelection({ from, to }) } catch (e) { /* seleção fora do range após edição concorrente — ignora */ }
		iniciarAutosave(novoEditor)
	}

	ruler.onDrop(margensPx => {
		reiniciarEditorComNovaMargem(margensPx)
		const emp = empreendimentoSelecionado()
		if (!emp) { return }
		fetch(`/documentos/empreendimentos/${emp.id}/margens/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
			body: JSON.stringify({
				margem_sup: Math.round(margensPx.top / MM_TO_PX),
				margem_dir: Math.round(margensPx.right / MM_TO_PX),
				margem_inf: Math.round(margensPx.bottom / MM_TO_PX),
				margem_esq: Math.round(margensPx.left / MM_TO_PX),
			}),
		})
	})
```

Substituir a seção **"Autosave 30s quando houver mudança"** existente no fim do arquivo (que fazia `setInterval` direto sobre `editor`) para usar a mesma função `iniciarAutosave`, chamando-a logo após `window._editor = editor` na inicialização original:

```js
	window._editor = editor
	iniciarAutosave(editor)
```

E remover o bloco antigo:
```js
	// ---- Autosave 30s quando houver mudança ----
	let sujo = false
	editor.on('update', () => { sujo = true })
	setInterval(() => {
		if (sujo) { sujo = false; salvar() }
	}, 30000)
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest documentos/tests/test_editor_ruler_drag.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add documentos/static/documentos/js/editor/ruler.js documentos/static/documentos/js/editor/editor-init.js \
        documentos/templates/documentos/modelo_editor.html documentos/tests/test_editor_ruler_drag.py
git commit -m "feat(documentos): drag page-margin ruler markers, reinit editor and persist margins"
```

---

### Task 6: Arrastar recuo de parágrafo

**Files:**
- Modify: `documentos/static/documentos/js/editor/ruler.js` (marcadores de recuo)
- Modify: `documentos/static/documentos/js/editor/editor-init.js` (sincroniza marcadores com o parágrafo do cursor)
- Test: `documentos/tests/test_editor_ruler_indent_drag.py` (novo)

**Interfaces:**
- Consumes: `IndentAttrsExtension` (Task 3), `ruler` do horizontal (Task 4/5).
- Produces: `ruler.onIndentDrop(callback)` — `callback({ indentLeft, indentRight, indentFirstLine })` em px, chamado no drop dos marcadores azul/vermelho.
- Produces: `ruler.setIndent({ indentLeft, indentRight, indentFirstLine })` — reposiciona os marcadores sem disparar `onIndentDrop` (usado quando o cursor muda de parágrafo).

- [ ] **Step 1: Escrever o teste (falhando)**

Criar `documentos/tests/test_editor_ruler_indent_drag.py`:

```python
import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Indent Drag Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Parágrafo alvo do recuo.</p>',
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_arrastar_marcador_de_recuo_atualiza_paragrafo(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.click('#tiptapEditor .ProseMirror p')

	marcador = page.locator('.doc-ruler-marcador-recuo-esquerdo')
	box = marcador.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()

	html_depois = page.evaluate('window._editor.getHTML()')
	assert 'margin-left:' in html_depois
	assert 'Parágrafo alvo do recuo' in html_depois
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest documentos/tests/test_editor_ruler_indent_drag.py -v`
Expected: FAIL (`.doc-ruler-marcador-recuo-esquerdo` não existe)

- [ ] **Step 3: Adicionar marcadores de recuo ao `ruler.js`**

Dentro de `init` (mesmo arquivo da Task 5), adicionar após a criação dos marcadores de margem de página:

```js
		const marcadorRecuoPrimeiraLinha = criarMarcador('recuo-primeira-linha', 'ew-resize')
		const marcadorRecuoEsquerdo = criarMarcador('recuo-esquerdo', 'ew-resize')
		const marcadorRecuoDireito = criarMarcador('recuo-direito', 'ew-resize')
		horiz.appendChild(marcadorRecuoPrimeiraLinha)
		horiz.appendChild(marcadorRecuoEsquerdo)
		horiz.appendChild(marcadorRecuoDireito)

		let indentAtual = { indentLeft: 0, indentRight: 0, indentFirstLine: 0 }
		let onIndentDropCb = null

		function repintarIndent() {
			const baseEsq = margens.left + indentAtual.indentLeft
			marcadorRecuoEsquerdo.style.left = `${baseEsq}px`
			marcadorRecuoPrimeiraLinha.style.left = `${baseEsq + indentAtual.indentFirstLine}px`
			marcadorRecuoDireito.style.left = `${pageWidthPx - margens.right - indentAtual.indentRight}px`
		}
		repintarIndent()

		function arrastarIndent(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				e.preventDefault()
				e.stopPropagation()
				function onMove(ev) {
					const rect = horiz.getBoundingClientRect()
					const x = Math.max(0, Math.min(pageWidthPx, ev.clientX - rect.left))
					aplicar(x)
					repintarIndent()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onIndentDropCb) { onIndentDropCb({ ...indentAtual }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		arrastarIndent(marcadorRecuoEsquerdo, x => { indentAtual.indentLeft = Math.round(x - margens.left) })
		arrastarIndent(marcadorRecuoPrimeiraLinha, x => {
			indentAtual.indentFirstLine = Math.round(x - margens.left - indentAtual.indentLeft)
		})
		arrastarIndent(marcadorRecuoDireito, x => {
			indentAtual.indentRight = Math.round(pageWidthPx - margens.right - x)
		})
```

E no objeto retornado por `init`, adicionar:

```js
			setIndent(novoIndent) {
				indentAtual = { ...indentAtual, ...novoIndent }
				repintarIndent()
			},
			onIndentDrop(callback) { onIndentDropCb = callback },
```

CSS no template (junto do resto):

```css
	.doc-ruler-marcador-recuo-primeira-linha,
	.doc-ruler-marcador-recuo-esquerdo,
	.doc-ruler-marcador-recuo-direito { background: #0d6efd; }
	.doc-ruler-marcador-recuo-direito { background: #dc3545; }
```

- [ ] **Step 4: Sincronizar recuo com o parágrafo do cursor em `editor-init.js`**

Adicionar após o wiring de `ruler.onDrop` (Task 5):

```js
	// ---- Recuo de parágrafo: sincroniza marcadores com o cursor e aplica no drop ----
	function atualizarMarcadoresDeRecuo() {
		const attrs = editorAtivo().getAttributes('paragraph')
		ruler.setIndent({
			indentLeft: attrs.indentLeft || 0,
			indentRight: attrs.indentRight || 0,
			indentFirstLine: attrs.indentFirstLine || 0,
		})
	}
	function editorAtivo() { return window._editor }
	editorAtivo().on('selectionUpdate', atualizarMarcadoresDeRecuo)
	editorAtivo().on('transaction', atualizarMarcadoresDeRecuo)

	ruler.onIndentDrop(novoIndent => {
		editorAtivo().chain().focus().updateAttributes('paragraph', novoIndent).run()
	})
```

Nota: como `reiniciarEditorComNovaMargem` (Task 5) troca `window._editor` por uma instância nova, os listeners `selectionUpdate`/`transaction` de recuo precisam ser re-registrados após cada reinício. Adicionar dentro de `reiniciarEditorComNovaMargem`, logo depois de `iniciarAutosave(novoEditor)`:

```js
		novoEditor.on('selectionUpdate', atualizarMarcadoresDeRecuo)
		novoEditor.on('transaction', atualizarMarcadoresDeRecuo)
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest documentos/tests/test_editor_ruler_indent_drag.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add documentos/static/documentos/js/editor/ruler.js documentos/static/documentos/js/editor/editor-init.js \
        documentos/templates/documentos/modelo_editor.html documentos/tests/test_editor_ruler_indent_drag.py
git commit -m "feat(documentos): drag paragraph indent markers on the ruler"
```

---

### Task 7: Teste E2E completo + screenshot

**Files:**
- Test: `documentos/tests/test_editor_ruler_e2e.py` (novo)

**Interfaces:**
- Consumes: tudo das Tasks 1-6.

- [ ] **Step 1: Escrever o teste E2E**

Criar `documentos/tests/test_editor_ruler_e2e.py`:

```python
import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def cenario_completo(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento E2E Régua', telefone='(83) 95555-5555',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=25, margem_dir=20, margem_inf=20, margem_esq=30)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato E2E Régua', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Cláusula primeira. Texto de teste E2E que deve sobreviver a tudo.</p>',
		criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo, empr


@pytest.mark.django_db
def test_fluxo_completo_regua_margem_e_recuo(logged_browser, live_server, cenario_completo):
	modelo, empr = cenario_completo
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')

	texto_original = page.evaluate('window._editor.getHTML()')
	assert 'Cláusula primeira' in texto_original

	page.select_option('#modeloEmpreendimento', str(empr.pk))

	marcador_margem = page.locator('.doc-ruler-marcador-margem-esquerda')
	box = marcador_margem.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 30, box['y'] + box['height'] / 2)
	page.mouse.up()
	page.wait_for_timeout(500)

	page.click('#tiptapEditor .ProseMirror p')
	marcador_indent = page.locator('.doc-ruler-marcador-recuo-esquerdo')
	box2 = marcador_indent.bounding_box()
	page.mouse.move(box2['x'] + box2['width'] / 2, box2['y'] + box2['height'] / 2)
	page.mouse.down()
	page.mouse.move(box2['x'] + box2['width'] / 2 + 20, box2['y'] + box2['height'] / 2)
	page.mouse.up()

	texto_final = page.evaluate('window._editor.getHTML()')
	assert 'Cláusula primeira' in texto_final
	assert 'margin-left:' in texto_final

	empr.refresh_from_db()
	cfg = ConfiguracaoDocumento.objects.get(empreendimento=empr)
	assert cfg.margem_esq != 30

	page.screenshot(path='documentos/tests/screenshots/editor_regua_e2e.png', full_page=True)
```

- [ ] **Step 2: Rodar o teste e confirmar que passa**

Run:
```bash
mkdir -p documentos/tests/screenshots
python -m pytest documentos/tests/test_editor_ruler_e2e.py -v
```
Expected: PASS, screenshot salvo em `documentos/tests/screenshots/editor_regua_e2e.png`

- [ ] **Step 3: Rodar a suíte inteira do app `documentos` pra checar regressão**

Run: `python -m pytest documentos/tests/ -v`
Expected: todos os testes passam (incluindo os das Tasks 1-6 e os já existentes antes deste plano)

- [ ] **Step 4: Commit**

```bash
git add documentos/tests/test_editor_ruler_e2e.py
git commit -m "test(documentos): add end-to-end test for the Word-style ruler flow"
```