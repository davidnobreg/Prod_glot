# Wizard de Update de Empreendimento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar um wizard de edição (6 steps, mesma UX do wizard de cadastro) para `Empreendimento`, operando sobre um objeto já ativo via mecanismo de draft-copy, sem alterar `views.py`/`forms.py`/`models.py`/migrations.

**Architecture:** `views_update.py` (novo) cria uma cópia inativa (`is_ativo=False`) do empreendimento real ao entrar no wizard; steps 1/2/3/5 editam essa cópia; step 4 (representantes) e documentos (empreendimento + representante) agem direto no objeto real via AJAX imediato; step 6 faz o commit final (`transaction.atomic()`, copia campos + endereços + logo draft→real) e apaga o draft. Reaproveita quase 100% de `forms.py`/`services.py`/`empreendimento_wizard.js` do wizard de cadastro já existente.

**Tech Stack:** Django (views baseadas em função, `ModelForm`, `modelformset_factory`), pytest via `django.test.TestCase`, JS vanilla (`fetch`) já existente.

## Global Constraints

- Não alterar `empreendimentos/views.py`, `empreendimentos/forms.py`, `empreendimentos/models.py`.
- Não gerar migration nova.
- Não alterar nenhum outro app.
- Não remover campos legados `representante_nome`/`representante_cpf`/`representante_rg` do `Empreendimento`.
- Não implementar cleanup de draft órfão (limitação aceita — ver spec).
- Todas as rotas novas usam `<uuid:empreendimento_uuid>` (nunca `<int:pk>`) — `empreendimentos/urls.py` já é 100% uuid.
- Permissão em toda view/endpoint novo: `@has_permission_decorator('alterarEmpreendimento')` (já existe em `core/roles.py`, é a mesma da view antiga `alteraEmpreendimento`) — nunca `'criarEmpreendimento'`.
- Arquivos novos (`views_update.py`, `forms_update.py`) usam indentação com **tabs** (convenção já usada em `services.py`, arquivo mais novo do app; `views.py`/`forms.py` legados usam espaços — não mexer neles). Edições em `urls.py` seguem o estilo já existente no arquivo (espaços).
- Toda remoção de documento (`DocumentoEmpreendimento`/`DocumentoRepresentante`) chama `arquivo.delete(save=False)` antes de `.delete()` — já garantido pelas funções existentes em `services.py`, reaproveitadas sem alteração.
- **Exceção pro campo `cnpj`**: `Empreendimento.cnpj` tem `unique=True` no
  banco (`empreendimentos/models.py:91`). Copiar `cnpj=real.cnpj` pro draft
  na criação estouraria `IntegrityError` (duas linhas ativas simultâneas —
  real ainda ativo + draft — com o mesmo CNPJ, mesmo o draft sendo
  `is_ativo=False`; unique constraint não distingue isso). Por isso `cnpj`
  **nunca é gravado na coluna do draft** (fica sempre `None` lá) — o valor
  pendente de edição do usuário é guardado em
  `request.session['wizard_update'][str(empreendimento_uuid)]['cnpj_pendente']`
  (string simples, sem problema de serialização — diferente do caso do
  `logo`) e só é aplicado no `real.cnpj` no commit final do step 6. Ver
  Tasks 2, 5 e 11.
- Testes que envolvem upload de arquivo usam `@override_settings(DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage', STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})` — mesmo padrão de `ImportarLotesTest` em `empreendimentos/tests/test_empreendimentos.py:116-122`, evita hit no B2 real durante o teste.
- Usuário de teste sempre `User.objects.create_user(username=..., password=..., is_superuser=True, is_staff=True)` — `has_permission_decorator` libera superuser (confirmado em `ExportarLotesTest`), evita depender de fixture de roles.

---

### Task 1: `services.sincronizar_endereco` — cópia/atualização de endereço reaproveitável

**Files:**
- Modify: `empreendimentos/services.py` (adicionar ao final do arquivo)
- Test: `empreendimentos/tests/test_wizard_update.py` (novo arquivo)

**Interfaces:**
- Produces: `empreendimentos.services.CAMPOS_ENDERECO` (tuple de 7 strings), `empreendimentos.services.sincronizar_endereco(endereco_destino, endereco_origem) -> Endereco` — se `endereco_origem` for `None`, retorna `endereco_destino` sem alterar nada; senão copia os campos de `endereco_origem` pra dentro de `endereco_destino` (criando um `Endereco` novo se `endereco_destino` for `None`, via `criar_ou_atualizar_endereco` já existente).

- [ ] **Step 1: Write the failing test**

Criar `empreendimentos/tests/test_wizard_update.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from base.models import Endereco
from empreendimentos import services as empreendimento_services
from empreendimentos.models import Empreendimento

User = get_user_model()


def make_user(username='update_wizard_user'):
	return User.objects.create_user(
		username=username, password='pass123', email=f'{username}@test.com',
		is_superuser=True, is_staff=True,
	)


def make_empreendimento(**kwargs):
	defaults = {
		'nome': 'Empreendimento Real', 'telefone': '(83) 99999-9999',
		'tempo_reserva': 30, 'quantidade_parcela': 60, 'cnpj': '11222333000181',
	}
	defaults.update(kwargs)
	return Empreendimento.objects.create(**defaults)


def make_endereco(**kwargs):
	defaults = {
		'cep': '58000000', 'rua': 'Rua Original', 'numero': '10',
		'complemento': '', 'bairro': 'Centro', 'cidade': 'João Pessoa', 'estado': 'PB',
	}
	defaults.update(kwargs)
	return Endereco.objects.create(**defaults)


class SincronizarEnderecoTest(TestCase):

	def test_origem_none_retorna_destino_sem_alterar(self):
		destino = make_endereco(rua='Fica igual')
		resultado = empreendimento_services.sincronizar_endereco(destino, None)
		self.assertEqual(resultado, destino)
		destino.refresh_from_db()
		self.assertEqual(destino.rua, 'Fica igual')

	def test_destino_none_cria_endereco_novo(self):
		origem = make_endereco(rua='Rua Origem', cidade='Campina Grande')
		resultado = empreendimento_services.sincronizar_endereco(None, origem)
		self.assertIsNotNone(resultado.pk)
		self.assertNotEqual(resultado.pk, origem.pk)
		self.assertEqual(resultado.rua, 'Rua Origem')
		self.assertEqual(resultado.cidade, 'Campina Grande')

	def test_destino_existente_e_atualizado_in_place(self):
		origem = make_endereco(rua='Rua Nova', numero='999')
		destino = make_endereco(rua='Rua Velha', numero='1')
		destino_pk = destino.pk
		resultado = empreendimento_services.sincronizar_endereco(destino, origem)
		self.assertEqual(resultado.pk, destino_pk)
		self.assertEqual(resultado.rua, 'Rua Nova')
		self.assertEqual(resultado.numero, '999')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `AttributeError: module 'empreendimentos.services' has no attribute 'sincronizar_endereco'`

- [ ] **Step 3: Write minimal implementation**

Adicionar ao final de `empreendimentos/services.py` (arquivo usa tabs):

```python
CAMPOS_ENDERECO = ('cep', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'estado')


def sincronizar_endereco(endereco_destino, endereco_origem):
	"""Copia os campos de `endereco_origem` pra dentro de `endereco_destino`
	(cria um Endereco novo se `endereco_destino` for None). Usado no
	mecanismo de draft-copy do wizard de update: espelhar um Endereco do
	real pro draft (destino=None) e depois copiar de volta do draft pro
	real no commit final (destino=endereco do real)."""
	if endereco_origem is None:
		return endereco_destino
	dados = {campo: getattr(endereco_origem, campo) for campo in CAMPOS_ENDERECO}
	return criar_ou_atualizar_endereco(dados, endereco=endereco_destino)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 3 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/services.py empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add sincronizar_endereco service helper"
```

---

### Task 2: Mecanismo de draft-copy — `_get_or_create_draft` / `_deletar_draft` / cancelar

**Files:**
- Create: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `empreendimento_services.sincronizar_endereco` (Task 1), `empreendimentos.models.Empreendimento`, `base.models.Endereco`.
- Produces: `views_update._WIZARD_UPDATE_SESSION_KEY` (str constante `'wizard_update'`), `views_update._get_or_create_draft(request, empreendimento_uuid) -> (real, draft)`, `views_update._deletar_draft(request, empreendimento_uuid) -> None`, `views_update.wizard_update_cancelar(request, empreendimento_uuid)` (view), url `wizard_update_cancelar`.

- [ ] **Step 1: Write the failing test**

Adicionar em `empreendimentos/tests/test_wizard_update.py`:

```python
from django.urls import reverse

from empreendimentos import views_update
from empreendimentos.models import Empreendimento


class GetOrCreateDraftTest(TestCase):

	def setUp(self):
		self.factory_endereco_empresa = make_endereco(rua='Rua Empresa')
		self.factory_endereco_empr = make_endereco(rua='Rua Empreendimento')
		self.real = make_empreendimento(
			endereco_empresa=self.factory_endereco_empresa,
			endereco_empreendimento=self.factory_endereco_empr,
		)

	def _fake_request(self):
		from django.test import RequestFactory
		request = RequestFactory().get('/')
		from django.contrib.sessions.backends.db import SessionStore
		request.session = SessionStore()
		return request

	def test_cria_draft_com_campos_copiados(self):
		request = self._fake_request()
		real, draft = views_update._get_or_create_draft(request, self.real.uuid)

		self.assertEqual(real.pk, self.real.pk)
		self.assertFalse(draft.is_ativo)
		self.assertNotEqual(draft.pk, real.pk)
		self.assertEqual(draft.nome, real.nome)
		self.assertIsNone(draft.cnpj)  # cnpj NUNCA vai pro draft (unique=True no banco, ver Global Constraints)
		wizard_session = request.session['wizard_update'][str(real.uuid)]
		self.assertEqual(wizard_session['cnpj_pendente'], real.cnpj)
		self.assertNotEqual(draft.endereco_empresa_id, real.endereco_empresa_id)
		self.assertEqual(draft.endereco_empresa.rua, 'Rua Empresa')
		self.assertNotEqual(draft.endereco_empreendimento_id, real.endereco_empreendimento_id)

	def test_segunda_chamada_reaproveita_mesmo_draft(self):
		request = self._fake_request()
		_, draft1 = views_update._get_or_create_draft(request, self.real.uuid)
		_, draft2 = views_update._get_or_create_draft(request, self.real.uuid)
		self.assertEqual(draft1.pk, draft2.pk)
		self.assertEqual(Empreendimento.objects.filter(is_ativo=False).count(), 1)

	def test_deletar_draft_remove_draft_e_enderecos_mas_nao_o_real(self):
		request = self._fake_request()
		_, draft = views_update._get_or_create_draft(request, self.real.uuid)
		draft_pk = draft.pk
		endereco_empresa_draft_pk = draft.endereco_empresa_id
		endereco_empr_draft_pk = draft.endereco_empreendimento_id

		views_update._deletar_draft(request, self.real.uuid)

		self.assertFalse(Empreendimento.objects.filter(pk=draft_pk).exists())
		self.assertFalse(Endereco.objects.filter(pk=endereco_empresa_draft_pk).exists())
		self.assertFalse(Endereco.objects.filter(pk=endereco_empr_draft_pk).exists())
		self.real.refresh_from_db()
		self.assertEqual(self.real.nome, 'Empreendimento Real')
		self.assertNotIn(str(self.real.uuid), request.session.get('wizard_update', {}))


class WizardUpdateCancelarViewTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()

	def test_cancelar_redireciona_e_nao_altera_real(self):
		self.client.get(reverse('empreendimento_update_step1', args=[self.real.uuid]))
		self.assertEqual(Empreendimento.objects.filter(is_ativo=False).count(), 1)

		response = self.client.get(reverse('wizard_update_cancelar', args=[self.real.uuid]))
		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))
		self.assertEqual(Empreendimento.objects.filter(is_ativo=False).count(), 0)
		self.real.refresh_from_db()
		self.assertTrue(self.real.is_ativo)
```

Nota: `test_cancelar_redireciona_e_nao_altera_real` já depende da view `wizard_update_step1` existir (Task 4) só pra criar o draft via GET real — como ela ainda não existe nesta task, comente/pule esse teste específico por enquanto (ou crie o draft direto via `views_update._get_or_create_draft` com uma request de `self.client`, mais simples): troque a primeira linha do teste por:

```python
	def test_cancelar_redireciona_e_nao_altera_real(self):
		from empreendimentos import views_update

		session = self.client.session

		class _FakeRequest:
			pass

		fake_request = _FakeRequest()
		fake_request.session = session
		views_update._get_or_create_draft(fake_request, self.real.uuid)
		session.save()

		response = self.client.get(reverse('wizard_update_cancelar', args=[self.real.uuid]))
```

`self.client.session` (padrão documentado do Django pra pré-popular sessão em teste) já deixa o cookie de sessão pronto pro `self.client.get` seguinte reaproveitar — não precisa reatribuir nada de volta no client. Isso evita depender da Task 4 nesta task.

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `ModuleNotFoundError: No module named 'empreendimentos.views_update'` (e depois `NoReverseMatch` pra `wizard_update_cancelar`/`empreendimento_update_step1`)

- [ ] **Step 3: Write minimal implementation**

Criar `empreendimentos/views_update.py`:

```python
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from base.models import Endereco

from .models import Empreendimento
from . import services as empreendimento_services

_WIZARD_UPDATE_SESSION_KEY = 'wizard_update'


def _copiar_logo(logo_origem, instance_destino):
	"""Copia o conteúdo de `logo_origem` (ImageField de outra instância)
	pro `logo` de `instance_destino` via ContentFile — nunca reaproveita o
	mesmo path de storage entre draft e real (cada Empreendimento tem seu
	próprio uuid no path, ver `_upload_logo_empreendimento` em models.py)."""
	if not logo_origem:
		return
	if instance_destino.logo:
		instance_destino.logo.delete(save=False)
	instance_destino.logo.save(
		logo_origem.name.rsplit('/', 1)[-1],
		ContentFile(logo_origem.read()),
		save=False,
	)


def _get_or_create_draft(request, empreendimento_uuid):
	"""Retorna (real, draft). Cria o draft (cópia inativa) na primeira
	chamada dessa sessão pra esse empreendimento; reaproveita nas
	seguintes via ponteiro salvo em `request.session`."""
	real = get_object_or_404(Empreendimento, uuid=empreendimento_uuid, is_ativo=True)

	wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
	session_key = str(empreendimento_uuid)
	draft_uuid = wizard_session.get(session_key, {}).get('draft_uuid')

	if draft_uuid:
		draft = Empreendimento.objects.filter(uuid=draft_uuid, is_ativo=False).first()
		if draft is not None:
			return real, draft

	endereco_empresa = empreendimento_services.sincronizar_endereco(None, real.endereco_empresa)
	endereco_empreendimento = empreendimento_services.sincronizar_endereco(None, real.endereco_empreendimento)

	draft = Empreendimento.objects.create(
		is_ativo=False,
		nome=real.nome,
		telefone=real.telefone,
		observacao=real.observacao,
		cnpj=None,  # nunca copiar: unique=True no banco colide com o do real (ver Global Constraints)
		razaoSocial=real.razaoSocial,
		codBanco=real.codBanco,
		banco=real.banco,
		agencia=real.agencia,
		conta=real.conta,
		matricula=real.matricula,
		cidade_foro=real.cidade_foro,
		tempo_reserva=real.tempo_reserva,
		quantidade_parcela=real.quantidade_parcela,
		desconto=real.desconto,
		tipo_correcao=real.tipo_correcao,
		endereco_empresa=endereco_empresa,
		endereco_empreendimento=endereco_empreendimento,
	)
	_copiar_logo(real.logo, draft)

	wizard_session[session_key] = {'draft_uuid': str(draft.uuid), 'cnpj_pendente': real.cnpj}
	request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
	request.session.modified = True

	return real, draft


def _deletar_draft(request, empreendimento_uuid):
	"""Apaga o draft (+ seus 2 enderecos + logo) e limpa o ponteiro da
	sessão. Não afeta o objeto real de forma alguma."""
	wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
	session_key = str(empreendimento_uuid)
	entrada = wizard_session.get(session_key)
	if entrada is None:
		return

	draft = Empreendimento.objects.filter(uuid=entrada['draft_uuid']).first()
	if draft is not None:
		if draft.endereco_empresa_id:
			Endereco.objects.filter(pk=draft.endereco_empresa_id).delete()
		if draft.endereco_empreendimento_id:
			Endereco.objects.filter(pk=draft.endereco_empreendimento_id).delete()
		if draft.logo:
			draft.logo.delete(save=False)
		draft.delete()

	del wizard_session[session_key]
	request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
	request.session.modified = True


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_cancelar(request, empreendimento_uuid):
	_deletar_draft(request, empreendimento_uuid)
	return redirect('lista-empreendimento-tabela')
```

Adicionar em `empreendimentos/urls.py`: importar `views_update` e registrar a rota. No topo do arquivo, junto do bloco de imports existente, adicionar:

```python
from . import views_update
```

E dentro de `urlpatterns`, logo após o bloco `# Wizard de cadastro de Empreendimento` (antes de `# Importação de dados`):

```python
    # =========================
    # Wizard de update de Empreendimento
    # =========================
    path(
        'editar/<uuid:empreendimento_uuid>/cancelar/',
        views_update.wizard_update_cancelar,
        name='wizard_update_cancelar'
    ),
```

A rota `empreendimento_update_step1` usada no teste ainda não existe (Task 4) — pra essa task rodar isolada, use a variante do teste sem depender dela (ver nota no Step 1).

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 6 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add draft-copy mechanism for update wizard"
```

---

### Task 3: `forms_update.py` — forms com exclusão de unicidade pro real

**Contexto do bug que esta task corrige:** `EmpreendimentoStep1Form.clean_nome` e
`EmpresaStep2Form.clean_cnpj` (em `forms.py`, reaproveitados sem alteração)
excluem da checagem de duplicidade só `self.instance.pk` — que, no wizard de
update, é o pk do **draft**, não do real. Sem correção, editar o step1/step2
sem mudar nome/CNPJ dispararia falso-positivo "já existe um empreendimento
ativo com este nome/CNPJ" (o próprio real, com pk diferente do draft, bate
na query). Correção: subclasses que também excluem `real_pk`.

**Files:**
- Create: `empreendimentos/forms_update.py`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `empreendimentos.forms.EmpreendimentoStep1Form`, `empreendimentos.forms.EmpresaStep2Form`.
- Produces: `forms_update.EmpreendimentoUpdateStep1Form(real_pk=..., ...)`, `forms_update.EmpresaUpdateStep2Form(real_pk=..., ...)` — mesma interface das forms base, + kwarg obrigatório `real_pk`.

- [ ] **Step 1: Write the failing test**

Adicionar em `empreendimentos/tests/test_wizard_update.py`:

```python
from empreendimentos import forms_update


class EmpreendimentoUpdateStep1FormTest(TestCase):

	def setUp(self):
		self.real = make_empreendimento(nome='Nome Original')
		self.draft = make_empreendimento(nome='Nome Original', is_ativo=False, cnpj=None)

	def test_nome_igual_ao_do_proprio_real_nao_gera_erro(self):
		form = forms_update.EmpreendimentoUpdateStep1Form(
			{'nome': 'Nome Original', 'telefone': '(83) 98888-8888', 'observacao': ''},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertTrue(form.is_valid(), form.errors)

	def test_nome_de_outro_empreendimento_ativo_gera_erro(self):
		make_empreendimento(nome='Outro Ativo', cnpj='11222333000280')
		form = forms_update.EmpreendimentoUpdateStep1Form(
			{'nome': 'Outro Ativo', 'telefone': '(83) 98888-8888', 'observacao': ''},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertFalse(form.is_valid())
		self.assertIn('nome', form.errors)


class EmpresaUpdateStep2FormTest(TestCase):

	def setUp(self):
		self.real = make_empreendimento(cnpj='11222333000181')
		# draft nunca guarda cnpj de verdade (unique=True no banco colide com
		# o do real) — ver Global Constraints e Task 2/5/11. Testando aqui só
		# a validação da form, que é independente de onde o valor é gravado.
		self.draft = make_empreendimento(nome='Draft', is_ativo=False, cnpj=None)

	def test_cnpj_igual_ao_do_proprio_real_nao_gera_erro(self):
		form = forms_update.EmpresaUpdateStep2Form(
			{'cnpj': '11222333000181', 'razaoSocial': 'Razao', 'codBanco': '', 'banco': '', 'agencia': '1', 'conta': '1'},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertTrue(form.is_valid(), form.errors)

	def test_cnpj_de_outro_empreendimento_ativo_gera_erro(self):
		make_empreendimento(nome='Outro', cnpj='44555666000122')
		form = forms_update.EmpresaUpdateStep2Form(
			{'cnpj': '44555666000122', 'razaoSocial': 'Razao', 'codBanco': '', 'banco': '', 'agencia': '1', 'conta': '1'},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertFalse(form.is_valid())
		self.assertIn('cnpj', form.errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `ModuleNotFoundError: No module named 'empreendimentos.forms_update'`

- [ ] **Step 3: Write minimal implementation**

Criar `empreendimentos/forms_update.py`:

```python
import re

from django.core.exceptions import ValidationError

from .forms import EmpreendimentoStep1Form, EmpresaStep2Form
from .models import Empreendimento


class EmpreendimentoUpdateStep1Form(EmpreendimentoStep1Form):
	"""Igual a EmpreendimentoStep1Form, mas a checagem de nome duplicado
	também exclui o pk do empreendimento REAL (não só o do draft que essa
	form está editando) — sem isso, manter o nome inalterado no wizard de
	update sempre bateria no próprio real e falsamente acusaria duplicata."""

	def __init__(self, *args, real_pk, **kwargs):
		self.real_pk = real_pk
		super().__init__(*args, **kwargs)

	def clean_nome(self):
		nome = self.cleaned_data.get('nome')
		if not nome:
			return nome

		qs = Empreendimento.objects.filter(nome__iexact=nome, is_ativo=True)
		qs = qs.exclude(pk=self.real_pk)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise ValidationError('Já existe um empreendimento ativo com este nome.')

		return nome


class EmpresaUpdateStep2Form(EmpresaStep2Form):
	"""Mesma correção de exclusão de real_pk, pro CNPJ."""

	def __init__(self, *args, real_pk, **kwargs):
		self.real_pk = real_pk
		super().__init__(*args, **kwargs)

	def clean_cnpj(self):
		cnpj = self.cleaned_data.get('cnpj')
		if not cnpj:
			return cnpj

		cnpj = re.sub(r'\D', '', cnpj)
		if len(cnpj) != 14:
			raise ValidationError('CNPJ deve conter exatamente 14 números.')

		qs = Empreendimento.objects.filter(cnpj=cnpj)
		qs = qs.exclude(pk=self.real_pk)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise ValidationError('Este CNPJ já está cadastrado.')

		return cnpj
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 10 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/forms_update.py empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update-safe forms with real_pk exclusion"
```

---

### Task 4: Step 1 — Dados gerais

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Create: `empreendimentos/templates/wizard/update/_base_wizard_update.html`
- Create: `empreendimentos/templates/wizard/update/step1_dados_gerais.html`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `_get_or_create_draft`, `forms_update.EmpreendimentoUpdateStep1Form`.
- Produces: `views_update._WIZARD_UPDATE_STEPS` (lista de tuplas, mesmo formato de `views._WIZARD_STEPS`), `views_update._wizard_update_render(request, template, current_step, real, context)`, `views_update.wizard_update_step1`, url `empreendimento_update_step1`.

- [ ] **Step 1: Write the failing test**

Adicionar em `empreendimentos/tests/test_wizard_update.py`:

```python
class WizardUpdateStep1Test(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento(nome='Nome Antigo')
		self.url = reverse('empreendimento_update_step1', args=[self.real.uuid])

	def test_get_pre_preenche_com_dados_do_real(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Nome Antigo')

	def test_post_valido_atualiza_draft_nao_real(self):
		response = self.client.post(self.url, {
			'nome': 'Nome Novo', 'telefone': '(83) 97777-7777', 'observacao': 'obs nova',
		})
		self.assertRedirects(response, reverse('empreendimento_update_step2', args=[self.real.uuid]))

		self.real.refresh_from_db()
		self.assertEqual(self.real.nome, 'Nome Antigo')

		draft = Empreendimento.objects.get(is_ativo=False)
		self.assertEqual(draft.nome, 'Nome Novo')
		self.assertEqual(draft.observacao, 'obs nova')

	def test_anonimo_bloqueado(self):
		self.client.logout()
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'empreendimento_update_step1' not found`

- [ ] **Step 3: Write minimal implementation**

Em `empreendimentos/views_update.py`, adicionar imports no topo (junto aos já existentes):

```python
from django.shortcuts import render
from django.contrib import messages

from .forms import EmpresaStep2Form, EmpreendimentoStep3Form, EnderecoForm
from . import forms_update
```

E adicionar (após `_deletar_draft`, antes de `wizard_update_cancelar`):

```python
_WIZARD_UPDATE_STEPS = [
	('Dados gerais', 'empreendimento_update_step1'),
	('Empresa', 'empreendimento_update_step2'),
	('Endereço', 'empreendimento_update_step3'),
	('Representantes', 'empreendimento_update_step4'),
	('Configurações', 'empreendimento_update_step5'),
	('Documentos', 'empreendimento_update_step6'),
]


def _wizard_update_render(request, template, current_step, real, context):
	context['wizard_steps'] = _WIZARD_UPDATE_STEPS
	context['current_step'] = current_step
	context['empreendimento'] = real
	return render(request, template, context)


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step1(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST':
		form = forms_update.EmpreendimentoUpdateStep1Form(
			request.POST, request.FILES, instance=draft, real_pk=real.pk,
		)
		if form.is_valid():
			form.save()
			return redirect('empreendimento_update_step2', empreendimento_uuid=empreendimento_uuid)
		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		form = forms_update.EmpreendimentoUpdateStep1Form(instance=draft, real_pk=real.pk)

	return _wizard_update_render(request, 'wizard/update/step1_dados_gerais.html', 1, real, {
		'form': form,
	})
```

Adicionar em `empreendimentos/urls.py`, dentro do bloco `# Wizard de update de Empreendimento`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/step1/',
        views_update.wizard_update_step1,
        name='empreendimento_update_step1'
    ),
```

Criar `empreendimentos/templates/wizard/update/_base_wizard_update.html` (idêntico a `wizard/_base_wizard.html`, trocando título e link ativo do breadcrumb):

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Editar Empreendimento{% endblock %}

{% block content %}
<style>
	.wiz-steps{background:#fff;border-radius:12px;padding:20px 32px 16px;margin-bottom:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,.08)}
	.wiz-steps-row{display:flex;align-items:flex-start}
	.wiz-step-col{display:flex;flex-direction:column;align-items:center;flex:1;position:relative}
	.wiz-step-col:not(:last-child)::after{content:'';position:absolute;top:14px;left:50%;width:100%;height:2px;background:#dde1e7;z-index:0}
	.wiz-step-col.done:not(:last-child)::after{background:#08789a}
	.wiz-step-circle{width:28px;height:28px;border-radius:50%;border:2px solid #dde1e7;background:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#bbb;position:relative;z-index:1;flex-shrink:0}
	.wiz-step-col.done .wiz-step-circle,.wiz-step-col.active .wiz-step-circle{background:#08789a;border-color:#08789a;color:#fff}
	.wiz-step-lbl{font-size:11px;color:#bbb;margin-top:5px;font-weight:600;text-align:center;white-space:nowrap}
	.wiz-step-col.active .wiz-step-lbl,.wiz-step-col.done .wiz-step-lbl{color:#08789a}

	.wiz-card{border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);border:1px solid #e9ecef;margin-bottom:1.5rem}
	.wiz-card .card-body{padding:1.5rem}
	.wiz-sec-head{display:flex;align-items:center;gap:8px;margin-bottom:1.1rem}
	.wiz-sec-head i{color:#08789a;font-size:14px}
	.wiz-sec-head span{font-size:12px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.06em}
	.wiz-sec-divider{flex:1;height:1px;background:#eef0f4;margin-left:10px}
	.wiz-inner-div{height:1px;background:#eef0f4;margin:1.25rem 0}

	.wiz-rep-card{border:1px solid #e4e8ee;border-radius:10px;overflow:hidden;margin-bottom:12px}
	.wiz-rep-head{display:flex;align-items:center;justify-content:space-between;padding:9px 16px;background:#f6f8fb;border-bottom:1px solid #e4e8ee}
	.wiz-rep-badge{font-size:10px;font-weight:700;color:#08789a;background:#dff2f2;padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:.04em}
	.wiz-rep-body{padding:16px 18px}
	.wiz-btn-add-rep{width:100%;display:flex;align-items:center;justify-content:center;gap:7px;padding:11px;border:2px dashed #b5d8d8;border-radius:8px;background:#f2fafa;color:#08789a;font-size:13px;font-weight:700;margin-top:4px}
	.wiz-btn-add-rep:hover{background:#08789a;color:#fff;border-style:solid}

	.wiz-cfg-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
	.wiz-cfg-card{background:#f6f8fb;border:1px solid #e4e8ee;border-radius:8px;padding:13px 15px}
	.wiz-cfg-card .hint{font-size:11px;color:#aaa;margin-top:5px;line-height:1.4}

	.wiz-doc-row{display:flex;align-items:center;gap:11px;padding:9px 13px;border:1px solid #e4e8ee;border-radius:8px;background:#fff;margin-bottom:8px}
	.wiz-doc-ic{width:32px;height:32px;background:#dff2f2;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#08789a;flex-shrink:0}
	.wiz-badge-std{font-size:10px;background:#dff2f2;color:#08789a;padding:1px 7px;border-radius:20px;font-weight:700;margin-left:5px}

	.wiz-action-bar{background:#fff;border-top:2px solid #e9ecef;padding:1rem 1.5rem;border-radius:0 0 12px 12px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.75rem;box-shadow:0 -2px 8px rgba(0,0,0,.05)}
</style>

<div class="content-header">
	<div class="container-fluid">
		<div class="row align-items-center">
			<div class="col">
				<h1 class="mb-0" style="font-size:1.4rem;font-weight:700;">Editar Empreendimento</h1>
				<nav aria-label="breadcrumb">
					<ol class="breadcrumb mb-0" style="font-size:.8rem;">
						<li class="breadcrumb-item"><a href="/">Início</a></li>
						<li class="breadcrumb-item">
							<a href="{% url 'lista-empreendimento-tabela' %}">Empreendimentos</a>
						</li>
						<li class="breadcrumb-item active">Editar</li>
					</ol>
				</nav>
			</div>
		</div>
	</div>
</div>

<section class="content">
	<div class="container-fluid">

		{% if messages %}
			{% for message in messages %}
				<div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
					{{ message }}
					<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
				</div>
			{% endfor %}
		{% endif %}

		<div class="wiz-steps">
			<div class="wiz-steps-row">
				{% for nome, url_name in wizard_steps %}
					<div class="wiz-step-col {% if forloop.counter == current_step %}active{% elif forloop.counter < current_step %}done{% endif %}">
						<div class="wiz-step-circle">
							{% if forloop.counter < current_step %}<i class="fas fa-check" style="font-size:10px"></i>{% else %}{{ forloop.counter }}{% endif %}
						</div>
						<div class="wiz-step-lbl">{{ nome }}</div>
					</div>
				{% endfor %}
			</div>
		</div>

		{% block step_content %}{% endblock %}

	</div>
</section>
{% endblock %}
```

Criar `empreendimentos/templates/wizard/update/step1_dados_gerais.html`:

```html
{% extends 'wizard/update/_base_wizard_update.html' %}

{% block step_content %}
<form method="post" enctype="multipart/form-data" novalidate>
	{% csrf_token %}

	<div class="card wiz-card">
		<div class="card-body">
			<div class="wiz-sec-head"><i class="fas fa-building"></i><span>Dados do empreendimento</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-6">
					<label class="form-label" for="{{ form.nome.id_for_label }}">Nome do empreendimento <span class="text-danger">*</span></label>
					{{ form.nome }}
					{% if form.nome.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.nome.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label" for="{{ form.telefone.id_for_label }}">Telefone de contato <span class="text-danger">*</span></label>
					{{ form.telefone }}
					{% if form.telefone.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.telefone.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-12">
					<label class="form-label" for="{{ form.observacao.id_for_label }}">Observações <span class="text-muted">opcional</span></label>
					{{ form.observacao }}
				</div>
			</div>

			<div class="wiz-inner-div"></div>
			<div class="wiz-sec-head"><i class="far fa-image"></i><span>Logo</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-6">
					{% if form.instance.logo %}
						<img src="{{ form.instance.logo.url }}" alt="Logo atual" style="max-height:60px;display:block;margin-bottom:8px;">
					{% endif %}
					{{ form.logo }}
					{% if form.logo.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.logo.errors|striptags }}</div>{% endif %}
				</div>
			</div>
		</div>
	</div>

	<div class="wiz-action-bar">
		<a href="{% url 'wizard_update_cancelar' empreendimento.uuid %}" class="btn btn-outline-danger" style="border-radius:8px;">
			<i class="fas fa-times me-1"></i>Cancelar
		</a>
		<button type="submit" class="btn" style="background:#08789a;color:#fff;border-radius:8px;">
			Próximo <i class="fas fa-arrow-right ms-1"></i>
		</button>
	</div>
</form>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 13 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/templates/wizard/update/ empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update wizard step1 (dados gerais)"
```

---

### Task 5: Step 2 — Empresa + endereço da empresa

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Create: `empreendimentos/templates/wizard/update/step2_empresa.html`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `forms_update.EmpresaUpdateStep2Form`, `EnderecoForm` (de `forms.py`, reaproveitada sem alteração), `empreendimento_services.criar_ou_atualizar_endereco`.
- Produces: `views_update.wizard_update_step2`, url `empreendimento_update_step2`.

- [ ] **Step 1: Write the failing test**

```python
class WizardUpdateStep2Test(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento(cnpj='11222333000181')
		self.url = reverse('empreendimento_update_step2', args=[self.real.uuid])

	def test_post_valido_atualiza_draft_e_endereco_do_draft(self):
		response = self.client.post(self.url, {
			'cnpj': '99888777000166', 'razaoSocial': 'Razao Nova',
			'codBanco': '001', 'banco': 'BANCO DO BRASIL', 'agencia': '1234', 'conta': '5678',
			'cep': '58101000', 'rua': 'Rua Nova Empresa', 'numero': '20',
			'complemento': '', 'bairro': 'Bairro Novo', 'cidade': 'Campina Grande', 'estado': 'PB',
		})
		self.assertRedirects(response, reverse('empreendimento_update_step3', args=[self.real.uuid]))

		draft = Empreendimento.objects.get(is_ativo=False)
		self.assertEqual(draft.razaoSocial, 'Razao Nova')
		self.assertIsNone(draft.cnpj)  # cnpj nunca vai pro draft — ver Global Constraints
		self.assertEqual(draft.endereco_empresa.rua, 'Rua Nova Empresa')

		session = self.client.session
		self.assertEqual(
			session['wizard_update'][str(self.real.uuid)]['cnpj_pendente'], '99888777000166'
		)

		self.real.refresh_from_db()
		self.assertIsNone(self.real.endereco_empresa)
		self.assertEqual(self.real.cnpj, '11222333000181')  # só aplica no commit final (Task 11)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'empreendimento_update_step2' not found`

- [ ] **Step 3: Write minimal implementation**

Adicionar em `empreendimentos/views_update.py` (após `wizard_update_step1`):

```python
@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step2(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	session_key = str(empreendimento_uuid)

	if request.method == 'POST':
		form = forms_update.EmpresaUpdateStep2Form(request.POST, instance=draft, real_pk=real.pk)
		form_endereco = EnderecoForm(request.POST, prefix='empresa', instance=draft.endereco_empresa)

		if form.is_valid() and form_endereco.is_valid():
			cnpj_pendente = form.cleaned_data['cnpj']
			empreendimento = form.save(commit=False)
			empreendimento.cnpj = None  # nunca grava no draft — ver Global Constraints
			empreendimento.endereco_empresa = empreendimento_services.criar_ou_atualizar_endereco(
				form_endereco.cleaned_data, endereco=draft.endereco_empresa
			)
			empreendimento.save()

			wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
			wizard_session[session_key]['cnpj_pendente'] = cnpj_pendente
			request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
			request.session.modified = True

			return redirect('empreendimento_update_step3', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		cnpj_pendente = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {}).get(session_key, {}).get('cnpj_pendente', real.cnpj)
		form = forms_update.EmpresaUpdateStep2Form(instance=draft, real_pk=real.pk, initial={'cnpj': cnpj_pendente})
		form_endereco = EnderecoForm(prefix='empresa', instance=draft.endereco_empresa)

	return _wizard_update_render(request, 'wizard/update/step2_empresa.html', 2, real, {
		'form': form, 'form_endereco': form_endereco,
	})
```

Nota: `initial={'cnpj': cnpj_pendente}` no GET faz o campo exibir o valor
pendente (ou o do real, se step2 nunca foi visitado) mesmo com
`draft.cnpj` sempre `None` — `initial` explícito por campo tem prioridade
sobre o valor derivado de `instance` nessa mesma chave, é o mecanismo
padrão do Django `ModelForm`.

Adicionar em `empreendimentos/urls.py`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/step2/',
        views_update.wizard_update_step2,
        name='empreendimento_update_step2'
    ),
```

Criar `empreendimentos/templates/wizard/update/step2_empresa.html` (idêntico a `wizard/step2_empresa.html`, trocando extends, cancelar e o link "Anterior"):

```html
{% extends 'wizard/update/_base_wizard_update.html' %}

{% block step_content %}
<form method="post" novalidate>
	{% csrf_token %}

	<div class="card wiz-card">
		<div class="card-body">
			<div class="wiz-sec-head"><i class="fas fa-briefcase"></i><span>Pessoa jurídica</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-6">
					<label class="form-label">CNPJ <span class="text-danger">*</span></label>
					{{ form.cnpj }}
					{% if form.cnpj.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.cnpj.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Razão social <span class="text-danger">*</span></label>
					{{ form.razaoSocial }}
					{% if form.razaoSocial.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.razaoSocial.errors|striptags }}</div>{% endif %}
				</div>
			</div>

			<div class="wiz-inner-div"></div>
			<div class="wiz-sec-head"><i class="fas fa-university"></i><span>Dados bancários</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-6">
					<label class="form-label">Banco <span class="text-danger">*</span></label>
					{{ form.banco }}
					{% if form.banco.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.banco.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Código do banco</label>
					{{ form.codBanco }}
				</div>
				<div class="col-md-6">
					<label class="form-label">Agência <span class="text-danger">*</span></label>
					{{ form.agencia }}
					{% if form.agencia.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.agencia.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Conta <span class="text-danger">*</span></label>
					{{ form.conta }}
					{% if form.conta.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form.conta.errors|striptags }}</div>{% endif %}
				</div>
			</div>

			<div class="wiz-inner-div"></div>
			<div class="wiz-sec-head"><i class="fas fa-map-marker-alt"></i><span>Endereço da empresa</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-3">
					<label class="form-label">CEP <span class="text-danger">*</span></label>
					{{ form_endereco.cep }}
					{% if form_endereco.cep.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.cep.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-7">
					<label class="form-label">Cidade <span class="text-danger">*</span></label>
					{{ form_endereco.cidade }}
					{% if form_endereco.cidade.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.cidade.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-2">
					<label class="form-label">Estado <span class="text-danger">*</span></label>
					{{ form_endereco.estado }}
					{% if form_endereco.estado.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.estado.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Bairro <span class="text-danger">*</span></label>
					{{ form_endereco.bairro }}
					{% if form_endereco.bairro.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.bairro.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Rua <span class="text-danger">*</span></label>
					{{ form_endereco.rua }}
					{% if form_endereco.rua.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.rua.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Número <span class="text-danger">*</span></label>
					{{ form_endereco.numero }}
					{% if form_endereco.numero.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.numero.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Complemento <span class="text-muted">opcional</span></label>
					{{ form_endereco.complemento }}
				</div>
			</div>
		</div>
	</div>

	<div class="wiz-action-bar">
		<a href="{% url 'wizard_update_cancelar' empreendimento.uuid %}" class="btn btn-outline-danger" style="border-radius:8px;">
			<i class="fas fa-times me-1"></i>Cancelar
		</a>
		<div class="d-flex gap-2">
			<a href="{% url 'empreendimento_update_step1' empreendimento.uuid %}" class="btn btn-outline-secondary" style="border-radius:8px;">
				<i class="fas fa-arrow-left me-1"></i>Anterior
			</a>
			<button type="submit" class="btn" style="background:#08789a;color:#fff;border-radius:8px;">
				Próximo <i class="fas fa-arrow-right ms-1"></i>
			</button>
		</div>
	</div>
</form>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 14 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/templates/wizard/update/step2_empresa.html empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update wizard step2 (empresa)"
```

---

### Task 6: Step 3 — Endereço do empreendimento

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Create: `empreendimentos/templates/wizard/update/step3_endereco.html`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `EmpreendimentoStep3Form` (de `forms.py`, reaproveitada sem alteração — sem bug de unicidade, não precisa de subclasse), `EnderecoForm`.
- Produces: `views_update.wizard_update_step3`, url `empreendimento_update_step3`.

- [ ] **Step 1: Write the failing test**

```python
class WizardUpdateStep3Test(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()
		self.url = reverse('empreendimento_update_step3', args=[self.real.uuid])

	def test_post_valido_atualiza_draft(self):
		response = self.client.post(self.url, {
			'matricula': 'MAT-999', 'cidade_foro': 'Mauriti - CE',
			'cep': '63160000', 'rua': 'Rua Loteamento', 'numero': '1',
			'complemento': '', 'bairro': 'Bairro X', 'cidade': 'Mauriti', 'estado': 'CE',
		})
		self.assertRedirects(response, reverse('empreendimento_update_step4', args=[self.real.uuid]))

		draft = Empreendimento.objects.get(is_ativo=False)
		self.assertEqual(draft.matricula, 'MAT-999')
		self.assertEqual(draft.endereco_empreendimento.cidade, 'Mauriti')

		self.real.refresh_from_db()
		self.assertEqual(self.real.matricula, '')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'empreendimento_update_step3' not found`

- [ ] **Step 3: Write minimal implementation**

Adicionar import em `empreendimentos/views_update.py`:

```python
from .forms import EmpreendimentoStep3Form
```

Adicionar view (após `wizard_update_step2`):

```python
@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step3(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST':
		form = EmpreendimentoStep3Form(request.POST, instance=draft)
		form_endereco = EnderecoForm(request.POST, prefix='empreendimento', instance=draft.endereco_empreendimento)

		if form.is_valid() and form_endereco.is_valid():
			empreendimento = form.save(commit=False)
			empreendimento.endereco_empreendimento = empreendimento_services.criar_ou_atualizar_endereco(
				form_endereco.cleaned_data, endereco=draft.endereco_empreendimento
			)
			empreendimento.save()
			return redirect('empreendimento_update_step4', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		form = EmpreendimentoStep3Form(instance=draft)
		form_endereco = EnderecoForm(prefix='empreendimento', instance=draft.endereco_empreendimento)

	return _wizard_update_render(request, 'wizard/update/step3_endereco.html', 3, real, {
		'form': form, 'form_endereco': form_endereco,
	})
```

Adicionar em `empreendimentos/urls.py`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/step3/',
        views_update.wizard_update_step3,
        name='empreendimento_update_step3'
    ),
```

Criar `empreendimentos/templates/wizard/update/step3_endereco.html` (idêntico a `wizard/step3_endereco.html`, extends/cancelar/anterior trocados):

```html
{% extends 'wizard/update/_base_wizard_update.html' %}

{% block step_content %}
<form method="post" novalidate>
	{% csrf_token %}

	<div class="card wiz-card">
		<div class="card-body">
			<div class="wiz-sec-head"><i class="fas fa-map-marker-alt"></i><span>Endereço do empreendimento</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-3">
					<label class="form-label">CEP <span class="text-danger">*</span></label>
					{{ form_endereco.cep }}
					{% if form_endereco.cep.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.cep.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-7">
					<label class="form-label">Cidade <span class="text-danger">*</span></label>
					{{ form_endereco.cidade }}
					{% if form_endereco.cidade.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.cidade.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-2">
					<label class="form-label">Estado <span class="text-danger">*</span></label>
					{{ form_endereco.estado }}
					{% if form_endereco.estado.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.estado.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Bairro <span class="text-danger">*</span></label>
					{{ form_endereco.bairro }}
					{% if form_endereco.bairro.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.bairro.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Rua / Estrada <span class="text-danger">*</span></label>
					{{ form_endereco.rua }}
					{% if form_endereco.rua.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.rua.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Número <span class="text-danger">*</span></label>
					{{ form_endereco.numero }}
					{% if form_endereco.numero.errors %}<div class="text-danger" style="font-size:.8rem;">{{ form_endereco.numero.errors|striptags }}</div>{% endif %}
				</div>
				<div class="col-md-6">
					<label class="form-label">Complemento / Referência <span class="text-muted">opcional</span></label>
					{{ form_endereco.complemento }}
				</div>
			</div>

			<div class="wiz-inner-div"></div>
			<div class="wiz-sec-head"><i class="fas fa-file-alt"></i><span>Registro e foro</span><div class="wiz-sec-divider"></div></div>
			<div class="row g-3">
				<div class="col-md-6">
					<label class="form-label">Matrícula do imóvel</label>
					{{ form.matricula }}
					<div class="text-muted" style="font-size:.75rem;">Número de matrícula registrado em cartório</div>
				</div>
				<div class="col-md-6">
					<label class="form-label">Cidade do foro</label>
					{{ form.cidade_foro }}
					<div class="text-muted" style="font-size:.75rem;">Comarca para resolução de disputas contratuais</div>
				</div>
			</div>
		</div>
	</div>

	<div class="wiz-action-bar">
		<a href="{% url 'wizard_update_cancelar' empreendimento.uuid %}" class="btn btn-outline-danger" style="border-radius:8px;">
			<i class="fas fa-times me-1"></i>Cancelar
		</a>
		<div class="d-flex gap-2">
			<a href="{% url 'empreendimento_update_step2' empreendimento.uuid %}" class="btn btn-outline-secondary" style="border-radius:8px;">
				<i class="fas fa-arrow-left me-1"></i>Anterior
			</a>
			<button type="submit" class="btn" style="background:#08789a;color:#fff;border-radius:8px;">
				Próximo <i class="fas fa-arrow-right ms-1"></i>
			</button>
		</div>
	</div>
</form>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 15 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/templates/wizard/update/step3_endereco.html empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update wizard step3 (endereco)"
```

---

### Task 7: Step 4 — Representantes (formset direto no real)

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Create: `empreendimentos/templates/wizard/update/step4_representantes.html`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `RepresentanteFormSet`, `DocumentoRepresentanteForm`, `EnderecoForm` (de `forms.py`), `empreendimento_services.atualizar_representante`, `empreendimento_services.criar_representante`.
- Produces: `views_update.wizard_update_step4`, url `empreendimento_update_step4`.

- [ ] **Step 1: Write the failing test**

```python
from empreendimentos.models import RepresentanteLegal


class WizardUpdateStep4Test(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()
		self.rep = RepresentanteLegal.objects.create(
			empreendimento=self.real, nome='Rep Antigo', documento='11122233344',
			cargo='Sócio',
		)
		self.url = reverse('empreendimento_update_step4', args=[self.real.uuid])

	def _management_form(self, total=1):
		return {
			'representante-TOTAL_FORMS': str(total),
			'representante-INITIAL_FORMS': '1',
			'representante-MIN_NUM_FORMS': '1',
			'representante-MAX_NUM_FORMS': '1000',
		}

	def test_get_lista_representantes_do_real(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Rep Antigo')

	def test_post_edita_representante_existente_direto_no_real(self):
		data = self._management_form()
		data.update({
			'representante-0-id': str(self.rep.pk),
			'representante-0-nome': 'Rep Editado',
			'representante-0-documento': '11122233344',
			'representante-0-cargo': 'Administrador',
			'representante-0-estado_civil': '',
			'representante-0-endereco': '',
			'representante-0-endereco-cep': '58000000',
			'representante-0-endereco-rua': 'Rua Rep',
			'representante-0-endereco-numero': '5',
			'representante-0-endereco-bairro': 'Bairro Rep',
			'representante-0-endereco-cidade': 'João Pessoa',
			'representante-0-endereco-estado': 'PB',
		})
		response = self.client.post(self.url, data)
		self.assertRedirects(response, reverse('empreendimento_update_step5', args=[self.real.uuid]))

		self.rep.refresh_from_db()
		self.assertEqual(self.rep.nome, 'REP EDITADO')
		self.assertEqual(self.rep.cargo, 'Administrador')

	def test_post_adiciona_representante_novo_no_real(self):
		data = self._management_form(total=2)
		data.update({
			'representante-0-id': str(self.rep.pk),
			'representante-0-nome': self.rep.nome,
			'representante-0-documento': self.rep.documento,
			'representante-0-cargo': self.rep.cargo,
			'representante-0-estado_civil': '',
			'representante-0-endereco-cep': '', 'representante-0-endereco-rua': '',
			'representante-0-endereco-numero': '', 'representante-0-endereco-bairro': '',
			'representante-0-endereco-cidade': '', 'representante-0-endereco-estado': '',
			'representante-1-id': '',
			'representante-1-nome': 'Rep Novo',
			'representante-1-documento': '55566677788',
			'representante-1-cargo': 'Sócio',
			'representante-1-estado_civil': '',
			'representante-1-endereco-cep': '58000000',
			'representante-1-endereco-rua': 'Rua Novo Rep',
			'representante-1-endereco-numero': '2',
			'representante-1-endereco-bairro': 'Bairro Novo',
			'representante-1-endereco-cidade': 'João Pessoa',
			'representante-1-endereco-estado': 'PB',
		})
		response = self.client.post(self.url, data)
		self.assertRedirects(response, reverse('empreendimento_update_step5', args=[self.real.uuid]))
		self.assertTrue(
			RepresentanteLegal.objects.filter(empreendimento=self.real, nome='REP NOVO').exists()
		)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'empreendimento_update_step4' not found`

- [ ] **Step 3: Write minimal implementation**

Adicionar imports em `empreendimentos/views_update.py`:

```python
from .forms import RepresentanteFormSet, DocumentoRepresentanteForm
from .models import RepresentanteLegal, DocumentoRepresentante
```

Adicionar view:

```python
@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step4(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	queryset = RepresentanteLegal.objects.filter(empreendimento=real, is_ativo=True).order_by('id')

	if request.method == 'POST':
		formset = RepresentanteFormSet(request.POST, queryset=queryset, prefix='representante')
		enderecos_forms = [
			EnderecoForm(request.POST, prefix=f'representante-{i}-endereco')
			for i in range(len(formset.forms))
		]

		if formset.is_valid() and all(f.is_valid() for f in enderecos_forms):
			for form, form_endereco in zip(formset.forms, enderecos_forms):
				if not form.cleaned_data or form.cleaned_data.get('DELETE'):
					continue
				representante = form.instance
				dados = {k: v for k, v in form.cleaned_data.items() if k != 'id'}
				if representante.pk:
					empreendimento_services.atualizar_representante(
						representante, dados, endereco_dados=form_endereco.cleaned_data
					)
				else:
					empreendimento_services.criar_representante(
						real, dados, endereco_dados=form_endereco.cleaned_data
					)
			return redirect('empreendimento_update_step5', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios dos representantes.')
		docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
		reps_docs = [
			form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
			for form in formset.forms
		]
		return _wizard_update_render(request, 'wizard/update/step4_representantes.html', 4, real, {
			'formset': formset, 'enderecos_forms': enderecos_forms,
			'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
			'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
			'empty_doc_form': DocumentoRepresentanteForm(),
		})

	formset = RepresentanteFormSet(queryset=queryset, prefix='representante')
	enderecos_forms = [
		EnderecoForm(prefix=f'representante-{i}-endereco', instance=form.instance.endereco if form.instance.pk else None)
		for i, form in enumerate(formset.forms)
	]
	docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
	reps_docs = [
		form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
		for form in formset.forms
	]
	return _wizard_update_render(request, 'wizard/update/step4_representantes.html', 4, real, {
		'formset': formset, 'enderecos_forms': enderecos_forms,
		'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
		'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
		'empty_doc_form': DocumentoRepresentanteForm(),
	})
```

Adicionar em `empreendimentos/urls.py`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/step4/',
        views_update.wizard_update_step4,
        name='empreendimento_update_step4'
    ),
```

Criar `empreendimentos/templates/wizard/update/step4_representantes.html` — idêntico a `wizard/step4_representantes.html` (Task de referência: `empreendimentos/templates/wizard/step4_representantes.html` lido integralmente durante o brainstorming), trocando:
- `{% extends 'wizard/_base_wizard.html' %}` → `{% extends 'wizard/update/_base_wizard_update.html' %}`
- `{% url 'lista-empreendimento-tabela' %}` (botão Cancelar) → `{% url 'wizard_update_cancelar' empreendimento.uuid %}`
- `{% url 'empreendimento_wizard_step3' %}` (botão Anterior) → `{% url 'empreendimento_update_step3' empreendimento.uuid %}`
- No bloco de script no final do arquivo, os 3 `{% url %}` passados pro `initRepresentantes` trocam de `empreendimento_wizard_representante_del`/`wizard_rep_doc_upload`/`wizard_rep_doc_remover` pra `wizard_update_rep_del`/`wizard_update_rep_doc_upload`/`wizard_update_rep_doc_del` (criados na Task 8), cada um recebendo também `empreendimento.uuid` como primeiro argumento posicional de `{% url %}` (rotas de update levam `empreendimento_uuid` + `rep_uuid`/`doc_uuid`):

```html
<script src="{% static 'js/empreendimento_wizard.js' %}"></script>
<script>
	document.addEventListener('DOMContentLoaded', function () {
		EmpreendimentoWizard.initRepresentantes({
			removeUrlTemplate: '{% url "wizard_update_rep_del" empreendimento.uuid "00000000-0000-0000-0000-000000000000" %}',
			docUploadUrlTemplate: '{% url "wizard_update_rep_doc_upload" empreendimento.uuid "00000000-0000-0000-0000-000000000000" %}',
			docRemoveUrlTemplate: '{% url "wizard_update_rep_doc_del" empreendimento.uuid "00000000-0000-0000-0000-000000000000" %}',
		});
	});
</script>
```

O restante do arquivo (cards de representante, `conjuge-section`, lista/upload de documentos, `<template id="empty-rep-template">`) é copiado sem nenhuma outra alteração — o JS (`empreendimento_wizard.js`) é 100% reaproveitado, sem mudanças.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 18 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/templates/wizard/update/step4_representantes.html empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update wizard step4 (representantes, direto no real)"
```

---

### Task 8: AJAX — remover representante, upload/remover documento do representante

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `empreendimento_services.desativar_representante`, `empreendimento_services.criar_documento_representante`, `empreendimento_services.remover_documento_representante`.
- Produces: `views_update._documento_json(documento)`, `views_update.wizard_update_rep_del`, `views_update.wizard_update_rep_doc_upload`, `views_update.wizard_update_rep_doc_del`, urls `wizard_update_rep_del`/`wizard_update_rep_doc_upload`/`wizard_update_rep_doc_del`.

- [ ] **Step 1: Write the failing test**

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings


class WizardUpdateRepDelTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()
		self.rep1 = RepresentanteLegal.objects.create(
			empreendimento=self.real, nome='Rep Um', documento='11111111111', cargo='Sócio')
		self.rep2 = RepresentanteLegal.objects.create(
			empreendimento=self.real, nome='Rep Dois', documento='22222222222', cargo='Sócio')

	def test_del_desativa_representante_do_real(self):
		url = reverse('wizard_update_rep_del', args=[self.real.uuid, self.rep1.uuid])
		response = self.client.post(url)
		self.assertEqual(response.json(), {'ok': True})
		self.rep1.refresh_from_db()
		self.assertFalse(self.rep1.is_ativo)


@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class WizardUpdateRepDocTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()
		self.rep = RepresentanteLegal.objects.create(
			empreendimento=self.real, nome='Rep Doc', documento='33333333333', cargo='Sócio')

	def test_upload_cria_documento_no_representante_do_real(self):
		url = reverse('wizard_update_rep_doc_upload', args=[self.real.uuid, self.rep.uuid])
		arquivo = SimpleUploadedFile('rg.pdf', b'conteudo-fake', content_type='application/pdf')
		response = self.client.post(url, {
			'categoria': 'rg_representante', 'nome': '', 'arquivo': arquivo,
		})
		data = response.json()
		self.assertTrue(data['ok'])
		self.assertEqual(self.rep.documentos.count(), 1)

	def test_remover_documento(self):
		documento = empreendimento_services.criar_documento_representante(
			self.rep, 'rg_representante',
			SimpleUploadedFile('rg.pdf', b'x', content_type='application/pdf'),
		)
		url = reverse('wizard_update_rep_doc_del', args=[self.real.uuid, documento.uuid])
		response = self.client.post(url)
		self.assertEqual(response.json(), {'ok': True})
		self.assertEqual(self.rep.documentos.count(), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'wizard_update_rep_del' not found`

- [ ] **Step 3: Write minimal implementation**

Adicionar imports em `empreendimentos/views_update.py`:

```python
from django.core.exceptions import ValidationError
from django.http import JsonResponse
```

Adicionar funções:

```python
def _documento_json(documento):
	ext = documento.arquivo.name.rsplit('.', 1)[-1].lower() if '.' in documento.arquivo.name else ''
	return {
		'uuid': str(documento.uuid),
		'nome_exibicao': documento.nome_exibicao(),
		'categoria': documento.categoria,
		'categoria_display': documento.get_categoria_display(),
		'url': documento.arquivo.url,
		'ext': ext,
	}


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_rep_del(request, empreendimento_uuid, rep_uuid):
	representante = get_object_or_404(
		RepresentanteLegal, uuid=rep_uuid, empreendimento__uuid=empreendimento_uuid, empreendimento__is_ativo=True,
	)
	empreendimento_services.desativar_representante(representante)
	return JsonResponse({'ok': True})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_rep_doc_upload(request, empreendimento_uuid, rep_uuid):
	representante = get_object_or_404(
		RepresentanteLegal, uuid=rep_uuid, empreendimento__uuid=empreendimento_uuid, empreendimento__is_ativo=True,
	)
	form = DocumentoRepresentanteForm(request.POST, request.FILES)
	if not form.is_valid():
		erros = '; '.join(f'{campo}: {", ".join(msgs)}' for campo, msgs in form.errors.items())
		return JsonResponse({'ok': False, 'error': erros}, status=400)

	try:
		documento = empreendimento_services.criar_documento_representante(
			representante,
			form.cleaned_data['categoria'],
			form.cleaned_data['arquivo'],
			nome=form.cleaned_data.get('nome', ''),
			usuario=request.user,
		)
	except ValidationError as e:
		return JsonResponse({'ok': False, 'error': '; '.join(e.messages)}, status=400)

	return JsonResponse({'ok': True, 'documento': _documento_json(documento)})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_rep_doc_del(request, empreendimento_uuid, doc_uuid):
	documento = get_object_or_404(
		DocumentoRepresentante, uuid=doc_uuid,
		representante__empreendimento__uuid=empreendimento_uuid,
		representante__empreendimento__is_ativo=True,
	)
	empreendimento_services.remover_documento_representante(documento)
	return JsonResponse({'ok': True})
```

Adicionar em `empreendimentos/urls.py`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/representante/<uuid:rep_uuid>/remover/',
        views_update.wizard_update_rep_del,
        name='wizard_update_rep_del'
    ),
    path(
        'editar/<uuid:empreendimento_uuid>/representante/<uuid:rep_uuid>/doc/upload/',
        views_update.wizard_update_rep_doc_upload,
        name='wizard_update_rep_doc_upload'
    ),
    path(
        'editar/<uuid:empreendimento_uuid>/representante/doc/<uuid:doc_uuid>/remover/',
        views_update.wizard_update_rep_doc_del,
        name='wizard_update_rep_doc_del'
    ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 21 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add AJAX endpoints for representante remove/docs in update wizard"
```

---

### Task 9: Step 5 — Configurações

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Create: `empreendimentos/templates/wizard/update/step5_configuracoes.html`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: nenhum form dedicado (mesmo padrão de `views.wizard_step5` — seta campos direto e chama `full_clean`).
- Produces: `views_update.wizard_update_step5`, url `empreendimento_update_step5`.

- [ ] **Step 1: Write the failing test**

```python
class WizardUpdateStep5Test(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento(tempo_reserva=10, quantidade_parcela=12)
		self.url = reverse('empreendimento_update_step5', args=[self.real.uuid])

	def test_post_valido_atualiza_draft_nao_real(self):
		response = self.client.post(self.url, {
			'tempo_reserva': '15', 'quantidade_parcela': '24',
			'desconto': '5', 'tipo_correcao': 'IPCA',
		})
		self.assertRedirects(response, reverse('empreendimento_update_step6', args=[self.real.uuid]))

		draft = Empreendimento.objects.get(is_ativo=False)
		self.assertEqual(draft.tempo_reserva, 15)
		self.assertEqual(draft.tipo_correcao, 'IPCA')

		self.real.refresh_from_db()
		self.assertEqual(self.real.tempo_reserva, 10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'empreendimento_update_step5' not found`

- [ ] **Step 3: Write minimal implementation**

Adicionar view em `empreendimentos/views_update.py`:

```python
_CAMPOS_STEP5 = ('tempo_reserva', 'quantidade_parcela', 'desconto', 'tipo_correcao')


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step5(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST':
		for campo in _CAMPOS_STEP5:
			if campo in request.POST:
				setattr(draft, campo, request.POST.get(campo))
		try:
			draft.full_clean(validate_unique=False)
			draft.save(update_fields=_CAMPOS_STEP5)
		except ValidationError as e:
			messages.error(request, '; '.join(e.messages) if hasattr(e, 'messages') else str(e))
			return _wizard_update_render(request, 'wizard/update/step5_configuracoes.html', 5, real, {})
		return redirect('empreendimento_update_step6', empreendimento_uuid=empreendimento_uuid)

	return _wizard_update_render(request, 'wizard/update/step5_configuracoes.html', 5, real, {
		'draft': draft,
	})
```

Nota: o contexto do template precisa dos valores do **draft** (não do `empreendimento`/real, que o `_wizard_update_render` já injeta) — o template usa `draft.tempo_reserva` etc, diferente do cadastro que usa `empreendimento.tempo_reserva` porque lá `empreendimento` no contexto já É o draft. Ver template abaixo.

Adicionar em `empreendimentos/urls.py`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/step5/',
        views_update.wizard_update_step5,
        name='empreendimento_update_step5'
    ),
```

Criar `empreendimentos/templates/wizard/update/step5_configuracoes.html`:

```html
{% extends 'wizard/update/_base_wizard_update.html' %}

{% block step_content %}
<form method="post" novalidate>
	{% csrf_token %}

	<div class="card wiz-card">
		<div class="card-body">
			<div class="wiz-sec-head"><i class="fas fa-sliders-h"></i><span>Configurações operacionais</span><div class="wiz-sec-divider"></div></div>
			<p class="text-muted" style="font-size:.85rem;">Parâmetros financeiros usados nas vendas e cobranças deste empreendimento.</p>

			<div class="wiz-cfg-grid">
				<div class="wiz-cfg-card">
					<label class="form-label">Tempo de reserva (dias) <span class="text-danger">*</span></label>
					<input type="number" name="tempo_reserva" class="form-control" min="1" value="{{ draft.tempo_reserva|default:'' }}" required>
					<div class="hint">Prazo máximo que um lote fica em reserva antes de ser liberado automaticamente</div>
				</div>
				<div class="wiz-cfg-card">
					<label class="form-label">Quantidade de parcelas <span class="text-danger">*</span></label>
					<input type="number" name="quantidade_parcela" class="form-control" min="1" value="{{ draft.quantidade_parcela|default:'' }}" required>
					<div class="hint">Número padrão de parcelas para financiamento</div>
				</div>
				<div class="wiz-cfg-card">
					<label class="form-label">Desconto padrão (%)</label>
					<input type="number" name="desconto" class="form-control" min="0" max="100" value="{{ draft.desconto|default:'0' }}">
					<div class="hint">Percentual aplicado por padrão nas propostas de venda</div>
				</div>
				<div class="wiz-cfg-card">
					<label class="form-label">Índice de correção <span class="text-danger">*</span></label>
					<select name="tipo_correcao" class="form-select">
						<option value="IGPM" {% if draft.tipo_correcao == 'IGPM' %}selected{% endif %}>IGPM</option>
						<option value="IPCA" {% if draft.tipo_correcao == 'IPCA' %}selected{% endif %}>IPCA</option>
						<option value="INCC" {% if draft.tipo_correcao == 'INCC' %}selected{% endif %}>INCC</option>
					</select>
					<div class="hint">Índice de correção monetária das parcelas</div>
				</div>
			</div>
		</div>
	</div>

	<div class="wiz-action-bar">
		<a href="{% url 'wizard_update_cancelar' empreendimento.uuid %}" class="btn btn-outline-danger" style="border-radius:8px;">
			<i class="fas fa-times me-1"></i>Cancelar
		</a>
		<div class="d-flex gap-2">
			<a href="{% url 'empreendimento_update_step4' empreendimento.uuid %}" class="btn btn-outline-secondary" style="border-radius:8px;">
				<i class="fas fa-arrow-left me-1"></i>Anterior
			</a>
			<button type="submit" class="btn" style="background:#08789a;color:#fff;border-radius:8px;">
				Próximo <i class="fas fa-arrow-right ms-1"></i>
			</button>
		</div>
	</div>
</form>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 22 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/templates/wizard/update/step5_configuracoes.html empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update wizard step5 (configuracoes)"
```

---

### Task 10: Step 6 — Documentos do empreendimento (GET + AJAX upload/remover, sem commit ainda)

**Files:**
- Modify: `empreendimentos/views_update.py`
- Modify: `empreendimentos/urls.py`
- Create: `empreendimentos/templates/wizard/update/step6_documentos.html`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `DocumentoEmpreendimentoForm`, `empreendimento_services.criar_documento_empreendimento`, `empreendimento_services.remover_documento_empreendimento`.
- Produces: `views_update.wizard_update_step6` (só GET nesta task — POST "finalizar" vem na Task 11), `views_update.wizard_update_doc_upload`, `views_update.wizard_update_doc_del`, urls correspondentes.

- [ ] **Step 1: Write the failing test**

```python
from empreendimentos.models import DocumentoEmpreendimento


@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class WizardUpdateStep6DocTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()

	def test_get_lista_documentos_do_real(self):
		documento = empreendimento_services.criar_documento_empreendimento(
			self.real, 'contrato_social',
			SimpleUploadedFile('cs.pdf', b'x', content_type='application/pdf'),
		)
		url = reverse('empreendimento_update_step6', args=[self.real.uuid])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, documento.nome_exibicao())

	def test_upload_cria_documento_no_real(self):
		url = reverse('wizard_update_doc_upload', args=[self.real.uuid])
		arquivo = SimpleUploadedFile('alvara.pdf', b'x', content_type='application/pdf')
		response = self.client.post(url, {'categoria': 'alvara', 'nome': '', 'arquivo': arquivo})
		data = response.json()
		self.assertTrue(data['ok'])
		self.assertEqual(self.real.documentos.count(), 1)

	def test_remover_documento_do_real(self):
		documento = empreendimento_services.criar_documento_empreendimento(
			self.real, 'alvara', SimpleUploadedFile('a.pdf', b'x', content_type='application/pdf'),
		)
		url = reverse('wizard_update_doc_del', args=[self.real.uuid, documento.uuid])
		response = self.client.post(url)
		self.assertEqual(response.json(), {'ok': True})
		self.assertEqual(self.real.documentos.count(), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `NoReverseMatch: Reverse for 'empreendimento_update_step6' not found`

- [ ] **Step 3: Write minimal implementation**

Adicionar import em `empreendimentos/views_update.py`:

```python
from .forms import DocumentoEmpreendimentoForm
from .models import DocumentoEmpreendimento
```

Adicionar views:

```python
@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step6(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	documentos = real.documentos.all().order_by('categoria', 'criado_em')

	return _wizard_update_render(request, 'wizard/update/step6_documentos.html', 6, real, {
		'documentos': documentos,
		'doc_form': DocumentoEmpreendimentoForm(),
	})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_doc_upload(request, empreendimento_uuid):
	real = get_object_or_404(Empreendimento, uuid=empreendimento_uuid, is_ativo=True)
	form = DocumentoEmpreendimentoForm(request.POST, request.FILES)
	if not form.is_valid():
		erros = '; '.join(f'{campo}: {", ".join(msgs)}' for campo, msgs in form.errors.items())
		return JsonResponse({'ok': False, 'error': erros}, status=400)

	documento = empreendimento_services.criar_documento_empreendimento(
		real,
		form.cleaned_data['categoria'],
		form.cleaned_data['arquivo'],
		nome=form.cleaned_data.get('nome', ''),
		usuario=request.user,
	)
	return JsonResponse({'ok': True, 'documento': _documento_json(documento)})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_doc_del(request, empreendimento_uuid, doc_uuid):
	documento = get_object_or_404(
		DocumentoEmpreendimento, uuid=doc_uuid,
		empreendimento__uuid=empreendimento_uuid, empreendimento__is_ativo=True,
	)
	empreendimento_services.remover_documento_empreendimento(documento)
	return JsonResponse({'ok': True})
```

Adicionar em `empreendimentos/urls.py`:

```python
    path(
        'editar/<uuid:empreendimento_uuid>/step6/',
        views_update.wizard_update_step6,
        name='empreendimento_update_step6'
    ),
    path(
        'editar/<uuid:empreendimento_uuid>/doc/upload/',
        views_update.wizard_update_doc_upload,
        name='wizard_update_doc_upload'
    ),
    path(
        'editar/<uuid:empreendimento_uuid>/doc/<uuid:doc_uuid>/remover/',
        views_update.wizard_update_doc_del,
        name='wizard_update_doc_del'
    ),
```

Criar `empreendimentos/templates/wizard/update/step6_documentos.html` (sem a seção "Modelos vinculados" do cadastro — fora de escopo desta feature, não pedida no prompt; sem botão "Salvar empreendimento" ainda, vem na Task 11):

```html
{% extends 'wizard/update/_base_wizard_update.html' %}
{% load static %}

{% block step_content %}

<div class="card wiz-card">
	<div class="card-body">
		<div class="wiz-sec-head"><i class="fas fa-folder-open"></i><span>Documentos do empreendimento</span><div class="wiz-sec-divider"></div></div>
		<p class="text-muted" style="font-size:.85rem;">Contrato social, matrícula, alvará e demais documentos do loteamento (PDF ou imagem, até 20MB).</p>

		<div id="empr-doc-list">
			{% for doc in documentos %}
				<div class="wiz-doc-row" data-doc-uuid="{{ doc.uuid }}">
					<div class="wiz-doc-ic"><i class="far {% if doc.extensao == 'pdf' %}fa-file-pdf{% else %}fa-file-image{% endif %}"></i></div>
					<div class="flex-grow-1">
						<div style="font-size:13px;font-weight:600;">{{ doc.nome_exibicao }}</div>
						<div class="text-muted" style="font-size:11px;">{{ doc.get_categoria_display }}</div>
					</div>
					<a href="{{ doc.arquivo.url }}" target="_blank" class="btn btn-outline-secondary btn-sm"><i class="fas fa-eye"></i></a>
					<button type="button" class="btn btn-outline-danger btn-sm btn-empr-doc-remove"><i class="fas fa-trash"></i></button>
				</div>
			{% empty %}
				<p class="text-muted" style="font-size:.85rem;" id="empr-doc-empty-msg">Nenhum documento anexado ainda.</p>
			{% endfor %}
		</div>

		<form id="form-empr-doc-upload" class="d-flex gap-2 align-items-end mt-3" enctype="multipart/form-data">
			<div style="min-width:220px;">
				<label class="form-label">Categoria</label>
				{{ doc_form.categoria }}
			</div>
			<div class="flex-grow-1">
				<label class="form-label">Nome (opcional)</label>
				{{ doc_form.nome }}
			</div>
			<div>
				<label class="form-label">Arquivo</label>
				{{ doc_form.arquivo }}
			</div>
			<button type="submit" class="btn btn-outline-secondary" id="btn-empr-doc-upload">
				<span class="btn-label"><i class="fas fa-paperclip me-1"></i>Anexar</span>
				<span class="spinner-border spinner-border-sm d-none" role="status"></span>
			</button>
		</form>
		<div class="text-danger mt-2 d-none" id="empr-doc-upload-error" style="font-size:.85rem;"></div>
	</div>
</div>

<form method="post">
	{% csrf_token %}
	<div class="wiz-action-bar">
		<a href="{% url 'wizard_update_cancelar' empreendimento.uuid %}" class="btn btn-outline-danger" style="border-radius:8px;">
			<i class="fas fa-times me-1"></i>Cancelar
		</a>
		<div class="d-flex gap-2">
			<a href="{% url 'empreendimento_update_step5' empreendimento.uuid %}" class="btn btn-outline-secondary" style="border-radius:8px;">
				<i class="fas fa-arrow-left me-1"></i>Anterior
			</a>
			<button type="submit" class="btn" style="background:#08789a;color:#fff;border-radius:8px;">
				<i class="far fa-save me-1"></i>Salvar empreendimento
			</button>
		</div>
	</div>
</form>

<script src="{% static 'js/empreendimento_wizard.js' %}"></script>
<script>
	document.addEventListener('DOMContentLoaded', function () {
		EmpreendimentoWizard.initDocumentosEmpreendimento({
			uploadUrl: '{% url "wizard_update_doc_upload" empreendimento.uuid %}',
			removeUrlTemplate: '{% url "wizard_update_doc_del" empreendimento.uuid "00000000-0000-0000-0000-000000000000" %}',
		});
	});
</script>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 25 tests ... OK` (o POST em `wizard_update_step6` sem `'finalizar'` no body ainda não faz nada — sem problema, coberto na Task 11)

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/urls.py empreendimentos/templates/wizard/update/step6_documentos.html empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): add update wizard step6 GET + doc AJAX endpoints"
```

---

### Task 11: Commit final do step 6 (draft → real, transaction.atomic)

**Files:**
- Modify: `empreendimentos/views_update.py`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `empreendimento_services.sincronizar_endereco` (Task 1), `_copiar_logo`, `_deletar_draft`.
- Produces: `wizard_update_step6` ganha o branch `POST` completo (finaliza o wizard).

- [ ] **Step 1: Write the failing test**

```python
class WizardUpdateStep6CommitTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento(
			nome='Nome Original', cnpj='11222333000181',
			endereco_empresa=make_endereco(rua='Rua Empresa Original'),
			endereco_empreendimento=make_endereco(rua='Rua Empreendimento Original'),
		)

	def test_finalizar_aplica_draft_no_real_e_apaga_draft(self):
		step1_url = reverse('empreendimento_update_step1', args=[self.real.uuid])
		self.client.post(step1_url, {
			'nome': 'Nome Editado', 'telefone': '(83) 96666-6666', 'observacao': 'nova obs',
		})

		step5_url = reverse('empreendimento_update_step5', args=[self.real.uuid])
		self.client.post(step5_url, {
			'tempo_reserva': '45', 'quantidade_parcela': '48', 'desconto': '10', 'tipo_correcao': 'INCC',
		})

		draft = Empreendimento.objects.get(is_ativo=False)
		draft_pk = draft.pk
		draft_endereco_empresa_pk = draft.endereco_empresa_id

		step6_url = reverse('empreendimento_update_step6', args=[self.real.uuid])
		response = self.client.post(step6_url, {'finalizar': '1'})
		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))

		self.real.refresh_from_db()
		self.assertEqual(self.real.nome, 'Nome Editado')
		self.assertEqual(self.real.observacao, 'nova obs')
		self.assertEqual(self.real.tempo_reserva, 45)
		self.assertEqual(self.real.tipo_correcao, 'INCC')
		self.assertTrue(self.real.is_ativo)

		self.assertFalse(Empreendimento.objects.filter(pk=draft_pk).exists())
		self.assertFalse(Endereco.objects.filter(pk=draft_endereco_empresa_pk).exists())

	def test_finalizar_aplica_cnpj_pendente_sem_estourar_unique(self):
		step2_url = reverse('empreendimento_update_step2', args=[self.real.uuid])
		self.client.post(step2_url, {
			'cnpj': '99888777000166', 'razaoSocial': 'Razao', 'codBanco': '', 'banco': '',
			'agencia': '1', 'conta': '1',
			'cep': '58101000', 'rua': 'Rua', 'numero': '1',
			'complemento': '', 'bairro': 'Bairro', 'cidade': 'Cidade', 'estado': 'PB',
		})

		draft = Empreendimento.objects.get(is_ativo=False)
		self.assertIsNone(draft.cnpj)  # confirma que nunca foi gravado no draft

		step6_url = reverse('empreendimento_update_step6', args=[self.real.uuid])
		response = self.client.post(step6_url, {'finalizar': '1'})
		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))

		self.real.refresh_from_db()
		self.assertEqual(self.real.cnpj, '99888777000166')

	def test_finalizar_atualiza_endereco_do_real_in_place(self):
		endereco_empresa_pk_original = self.real.endereco_empresa_id

		step2_url = reverse('empreendimento_update_step2', args=[self.real.uuid])
		self.client.post(step2_url, {
			'cnpj': '11222333000181', 'razaoSocial': 'Razao', 'codBanco': '', 'banco': '',
			'agencia': '1', 'conta': '1',
			'cep': '58101000', 'rua': 'Rua Empresa Editada', 'numero': '99',
			'complemento': '', 'bairro': 'Bairro Editado', 'cidade': 'Campina Grande', 'estado': 'PB',
		})

		step6_url = reverse('empreendimento_update_step6', args=[self.real.uuid])
		self.client.post(step6_url, {'finalizar': '1'})

		self.real.refresh_from_db()
		self.assertEqual(self.real.endereco_empresa_id, endereco_empresa_pk_original)
		self.assertEqual(self.real.endereco_empresa.rua, 'Rua Empresa Editada')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: falha — POST em `wizard_update_step6` hoje (Task 10) não trata `'finalizar'`, response não redireciona (renderiza a página de novo, status 200), `assertRedirects` falha.

- [ ] **Step 3: Write minimal implementation**

Substituir `wizard_update_step6` em `empreendimentos/views_update.py` por:

```python
_CAMPOS_COMMIT_ESCALARES = (
	# 'cnpj' de propósito fora daqui — nunca fica no draft (unique=True no
	# banco), é aplicado à parte via `cnpj_pendente` da sessão (ver abaixo).
	'nome', 'telefone', 'observacao', 'razaoSocial',
	'codBanco', 'banco', 'agencia', 'conta', 'matricula',
	'cidade_foro', 'tempo_reserva', 'quantidade_parcela',
	'desconto', 'tipo_correcao',
)


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step6(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	documentos = real.documentos.all().order_by('categoria', 'criado_em')

	if request.method == 'POST' and 'finalizar' in request.POST:
		session_key = str(empreendimento_uuid)
		wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
		cnpj_pendente = wizard_session.get(session_key, {}).get('cnpj_pendente', real.cnpj)

		with transaction.atomic():
			for campo in _CAMPOS_COMMIT_ESCALARES:
				setattr(real, campo, getattr(draft, campo))
			real.cnpj = cnpj_pendente

			_copiar_logo(draft.logo, real)

			real.endereco_empresa = empreendimento_services.sincronizar_endereco(
				real.endereco_empresa, draft.endereco_empresa
			)
			real.endereco_empreendimento = empreendimento_services.sincronizar_endereco(
				real.endereco_empreendimento, draft.endereco_empreendimento
			)

			real.full_clean(validate_unique=False)
			real.save()

		_deletar_draft(request, empreendimento_uuid)
		messages.success(request, 'Empreendimento atualizado com sucesso.')
		return redirect('lista-empreendimento-tabela')

	return _wizard_update_render(request, 'wizard/update/step6_documentos.html', 6, real, {
		'documentos': documentos,
		'doc_form': DocumentoEmpreendimentoForm(),
	})
```

Adicionar import de `transaction` no topo de `empreendimentos/views_update.py`:

```python
from django.db import transaction
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 28 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/views_update.py empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): commit draft to real on update wizard step6 finalize"
```

---

### Task 12: Ligar botão "Editar" + suíte completa + smoke test manual

**Files:**
- Modify: `empreendimentos/templates/lista-empreendimentos-tabela.html:176-180`
- Test: `empreendimentos/tests/test_wizard_update.py`

**Interfaces:**
- Consumes: `empreendimento_update_step1` (Task 4).
- Produces: nenhuma interface nova — task de integração/wiring final.

- [ ] **Step 1: Write the failing test**

```python
class BotaoEditarListaTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()

	def test_lista_aponta_editar_pro_wizard_update(self):
		response = self.client.get(reverse('lista-empreendimento-tabela'))
		url_esperada = reverse('empreendimento_update_step1', args=[self.real.uuid])
		self.assertContains(response, url_esperada)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `AssertionError` — a resposta ainda contém `/alterar_empreendimento/<uuid>/`, não a nova URL.

- [ ] **Step 3: Write minimal implementation**

Em `empreendimentos/templates/lista-empreendimentos-tabela.html:176-180`, trocar:

```html
<a href="{% url 'alterar-empreendimento' empreendimento.uuid %}"
   class="btn btn-outline-warning action-btn" title="Editar"
   data-bs-toggle="tooltip">
    <i class="fas fa-edit"></i>
</a>
```

por:

```html
<a href="{% url 'empreendimento_update_step1' empreendimento.uuid %}"
   class="btn btn-outline-warning action-btn" title="Editar"
   data-bs-toggle="tooltip">
    <i class="fas fa-edit"></i>
</a>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test empreendimentos.tests.test_wizard_update -v 2`
Expected: `Ran 29 tests ... OK`

Rodar a suíte completa do app pra garantir zero regressão:

Run: `python manage.py test empreendimentos -v 2`
Expected: todos os testes existentes + os 28 novos passam.

Rodar a suíte completa do projeto:

Run: `python manage.py test`
Expected: mesma contagem de sucesso que a baseline já documentada em memória do projeto (299 passed / 2 failed pré-existentes de mojibake / 1 skipped), + os novos testes deste plano.

- [ ] **Step 5: Commit**

```bash
git add empreendimentos/templates/lista-empreendimentos-tabela.html empreendimentos/tests/test_wizard_update.py
git commit -m "feat(empreendimentos): point Editar button to update wizard"
```

- [ ] **Step 6: Smoke test manual (browser, não automatizado)**

Com o servidor local rodando (`python manage.py runserver`), logado como usuário com permissão `alterarEmpreendimento`:

1. Abrir `/empreendimentos/listar_empreendimento/`, clicar "Editar" num empreendimento com representantes e documentos reais — confirmar redirect pro step1 do wizard update com campos pré-preenchidos.
2. Alterar nome (step1), CNPJ (step2), CEP do empreendimento (step3) — confirmar avanço de step sem erro.
3. Step4: editar nome de um representante existente, clicar "Adicionar outro representante", preencher e clicar "Próximo" — confirmar que o novo aparece depois em `RepresentanteLegal.objects.filter(empreendimento=real)` via shell.
4. No mesmo step4, testar upload de documento num representante já existente (sem precisar do "Próximo") — confirmar que aparece na lista sem reload de página.
5. Step6: upload de documento do empreendimento, sem reload.
6. Clicar "Salvar empreendimento" no step6 — confirmar mensagem de sucesso, redirect pra listagem, e via shell (`Empreendimento.objects.filter(is_ativo=False)`) que não sobrou draft órfão.
7. Repetir o fluxo até o step3, clicar "Cancelar" — confirmar que o real não mudou nada e não sobrou draft (`Empreendimento.objects.filter(is_ativo=False).count() == 0`).
8. Verificar no Django admin (ou shell) que o logo do real (se enviado um novo no step1) aponta pra um arquivo físico existente, e que o logo antigo (se havia) foi removido do storage.

---

## Self-Review

**Spec coverage:** arquitetura de draft-copy (Tasks 2, 11), correções de path/uuid/permissão/redirect (constraints globais + Tasks 4-12), `sincronizar_endereco` (Task 1), bug de unicidade nome/CNPJ (Task 3), 6 steps (Tasks 4,5,6,7,9,10-11), AJAX de representante e documentos sempre no real (Tasks 7,8,10), cancelar (Task 2), botão Editar (Task 12), smoke test (Task 12 Step 6) — todos os itens do spec `docs/superpowers/specs/2026-07-13-wizard-update-empreendimento-design.md` têm task correspondente.

**Placeholder scan:** nenhum "TBD"/"implementar depois" — todo código é completo e executável; onde um template é "cópia com N trocas pontuais" (steps 3/4), as trocas exatas foram listadas literalmente, não deixadas vagas.

**Type consistency:** `_get_or_create_draft(request, empreendimento_uuid) -> (real, draft)` usado com a mesma assinatura em todas as views (Tasks 4-11); `_documento_json` definido uma vez (Task 8) e reaproveitado igual em Task 10 sem redefinir; `_CAMPOS_STEP5`/`_CAMPOS_COMMIT_ESCALARES`/`CAMPOS_ENDERECO` cada um definido uma única vez e importado/reaproveitado onde necessário.

**Correção feita durante a escrita do plano (não estava no spec):**
`Empreendimento.cnpj` tem `unique=True` no banco — copiar `cnpj=real.cnpj`
pro draft na criação (como o desenho original do mecanismo de draft-copy
previa pra todos os campos escalares) estouraria `IntegrityError` assim
que o real tivesse CNPJ preenchido (praticamente sempre). Corrigido:
`cnpj` nunca é gravado na coluna do draft, valor pendente vive em
`request.session[...]['cnpj_pendente']` (string simples, sem risco de
serialização) e só é aplicado ao real no commit final do step 6 (Tasks 2,
5, 11). Todos os demais campos escalares copiados no draft não têm
constraint `unique` no banco — só `cnpj` precisava desse tratamento.
