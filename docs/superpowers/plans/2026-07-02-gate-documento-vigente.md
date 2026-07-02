# Gate de Documento Vigente (Regra 1) — Plano de Implementação

> **Para quem for executar:** este plano NÃO segue o formato TDD passo-a-passo padrão da
> skill `superpowers:writing-plans` — usa "diff conceitual" por pedido explícito do autor
> do plano. Cada task ainda é independentemente testável e ordenada por dependência.
> Sugestão de execução: **superpowers:subagent-driven-development**, uma task por vez,
> revisão entre tasks (o Task 5 em especial reescreve fixtures de teste existentes e
> merece revisão humana antes de commit).

**Objetivo:** Substituir o critério implícito de "documento vigente" (status !=
arquivado aplicado por convenção) por um critério explícito e centralizado, e usar esse
critério para gatear geração de contrato e efetivação de venda — sem quebrar vendas já
em andamento em produção.

**Arquitetura:** Manager customizado em `VendaDocumento` centraliza o filtro "vigente".
`_tipos_disponiveis()` e `EfetivarVendaView` passam a exigir `documento_gerado` vinculado
(prova de que o documento aprovado tem lastro num `DocumentoGerado` real, não é upload
avulso). Um management command roda a mesma query de risco em produção e permite
backfill antes do gate entrar em vigor.

**Tech Stack:** Django 4.x, pytest-django (testes já existentes em `vendas/tests/` e
`documentos/tests/`).

## Premissas (já investigadas, não reabrir)

- `VendaDocumento.documento_gerado` já existe no schema (nullable, `SET_NULL`) — nenhuma
  migration de schema neste plano.
- Critério de "vigente" hoje = `status != 'arquivado'`, replicado manualmente em
  `ReservadoDetalheView`, `PreVendaDetalheView` e `CancelarReservaView`
  (`vendas/views/detail_views.py` e `vendas/views/delete_views.py`).
- `aceite_proposta` é campo morto — fora de escopo, não tocar.
- `CriarVendaView` tem buraco de segurança conhecido (sem checagem server-side) — escopo
  separado, não incluir aqui.
- Venda 301 (uuid `19803c1b-1e00-4a73-bd15-07845471dee5`) tem `proposta_assinada`
  aprovado sem `documento_gerado`, ativa em PRE-VENDA — trava assim que o gate (Task 4)
  entrar no ar. Task 3 existe para resolver isso ANTES do deploy de 4/5.
- **Query de risco rodada em 2026-07-02** contra o banco de dev real
  (`glot_teste@172.16.51.3`, mesmo host configurado em `configuration/.env`), via SQL
  direto (`vendas_registervenda` join `vendas_vendadocumento`):
  - `proposta_assinada` aprovado + `documento_gerado_id IS NULL` + venda ativa em
    RESERVADO/PRE-VENDA: **1 caso** — confirma exatamente a venda 301, nenhum outro.
  - `contrato_assinado` aprovado + `documento_gerado_id IS NULL` + venda ativa em
    RESERVADO/PRE-VENDA: **0 casos**.
  - Isso é o banco de dev, não produção — o mesmo relatório (Task 3, agora generalizado
    pros dois tipos) precisa rodar em produção antes do deploy de Task 4/5; dev com 0
    casos de contrato não garante 0 em produção, só reduz a probabilidade.

---

## Task 1 — Manager `vigentes()` em `VendaDocumento`

**Por quê primeiro:** Task 4 e Task 5 consomem esse manager. Sem ele, qualquer código
novo corre o risco de esquecer o `exclude(status='arquivado')` — exatamente o bug que
este plano existe pra evitar.

**Arquivos:**
- Modificar: `vendas/models.py` (linha ~83, classe `VendaDocumento`)
- Modificar: `vendas/views/detail_views.py` (3 pontos: `ReservadoDetalheView` ~L301,
  `PreVendaDetalheView` ~L380, `VendaDocumentoUploadView` ~L412)
- Modificar: `vendas/views/delete_views.py` (`CancelarReservaView` ~L72-75)
- Sem migration — `use_in_migrations` não é setado por `.as_manager()`, Django não
  rastreia troca de manager.

**Diff conceitual — `vendas/models.py`:**

```python
class VendaDocumento(models.Model):

	TIPO_CHOICES = [...]
	STATUS_CHOICES = [...]

	objects = VendaDocumentoQuerySet.as_manager()   # NOVO — antes da classe: querySet

	venda = models.ForeignKey(...)
	...
```

Antes da classe `VendaDocumento`, adicionar:

```python
class VendaDocumentoQuerySet(models.QuerySet):
	def vigentes(self):
		return self.exclude(status='arquivado')
```

**Diff conceitual — `vendas/views/detail_views.py`:**

```python
# ReservadoDetalheView.get_context_data (~L299)
context['venda_documentos'] = (
	VendaDocumento.objects.filter(venda=venda)
	.vigentes()                                          # antes: .exclude(status='arquivado')
	.select_related('enviado_por', 'aprovado_por', 'documento_gerado')
	if venda else VendaDocumento.objects.none()
)

# PreVendaDetalheView.get (~L380)
docs_venda = VendaDocumento.objects.filter(venda=venda).vigentes()   # antes: .exclude(status='arquivado')

# VendaDocumentoUploadView.post (~L410)
ciclo_atual = (
	VendaDocumento.objects.filter(venda=venda)
	.vigentes()                                          # antes: .exclude(status='arquivado')
	.aggregate(Max('ciclo'))['ciclo__max'] or 1
)
```

**Diff conceitual — `vendas/views/delete_views.py` (`CancelarReservaView`, ~L72):**

```python
# antes
VendaDocumento.objects.filter(
	venda=venda,
	status__in=['pendente', 'enviado', 'aprovado'],
).update(status='arquivado')

# depois
VendaDocumento.objects.filter(venda=venda).vigentes().update(status='arquivado')
```

**⚠️ Mudança de comportamento de negócio (não é refactor puro):** o filtro antigo de
`CancelarReservaView` excluía `rejeitado` da lista arquivada — `status__in=['pendente',
'enviado', 'aprovado']`. `.vigentes()` também arquiva `rejeitado`. Decisão tomada aqui,
não é acidente do jeito que o filtro unificado ficou: **rejeitado deve ser arquivado ao
cancelar**, porque a `RegisterVenda` não é apagada no cancelamento (`CancelarReservaView`
só marca `tipo_venda='CANCELADA'`, `is_ativo=False` — o registro e seus
`documentos_assinados` continuam existindo e são consultáveis). Sem essa mudança, um
documento rejeitado numa venda cancelada fica pra sempre fora de `arquivado`, e qualquer
`.vigentes()` futuro que rode sobre essa venda (ex.: uma tela de auditoria, ou reabertura
manual do registro) o trataria como "vigente" numa venda morta — estado inconsistente.
`aprovado`/`enviado`/`pendente` já eram arquivados antes; `rejeitado` fechava essa lacuna
por omissão, não por escolha.

Por ser mudança de comportamento, **não pode ir no PR "de baixo risco" sem cobertura de
teste dedicada** — ver tabela final: Task 1 sai do lote silencioso e exige revisão do
teste abaixo antes de aprovar o PR.

```python
# vendas/tests/test_delete_views.py (arquivo novo)
def test_cancelar_reserva_arquiva_documento_rejeitado(client, admin_user, venda):
	VendaDocumento.objects.create(
		venda=venda, tipo='outros', status='rejeitado', ciclo=1,
		arquivo_assinado='fake/rej.pdf', enviado_por=admin_user,
	)
	client.force_login(admin_user)
	client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
	doc = VendaDocumento.objects.get(venda=venda)
	assert doc.status == 'arquivado'
```
(URL confirmada em `vendas/urls.py:55` — `CancelarReservaView` está registrada em dois
nomes, `delete-reservado-lista` e `delete-reservado`; usar o segundo.)

**Testes existentes que quebram:** nenhum. Os 3 call sites em `detail_views.py` são
troca 1:1 (`.exclude(status='arquivado')` ≡ `.vigentes()`), os testes
`test_venda_documentos_excluem_arquivados` e `test_historico_por_ciclo_agrupa_arquivados`
continuam passando sem alteração.

**Risco de regressão:** baixo nos 3 call sites de leitura (`detail_views.py`, troca
1:1). **Médio no `CancelarReservaView`** — mudança de comportamento deliberada (arquiva
`rejeitado` agora), coberta pelo teste novo acima; esse teste é condição para aprovar o
PR desta task, não um nice-to-have.

---

## Task 2 — Preencher `documento_gerado` no upload

**Decisão:** vínculo **automático**, não seletor manual. Justificativa: o objetivo do
campo é rastreabilidade (provar que o documento assinado corresponde a um
`DocumentoGerado` real); um dropdown manual reintroduz exatamente o erro humano que o
gate tenta eliminar. Automático é tecnicamente viável porque `DocumentoGerado.venda` e
`DocumentoGerado.modelo.tipo` já existem — dá pra casar por venda + tipo sem ambiguidade
na maioria dos casos.

**Mapeamento necessário:** `VendaDocumento.tipo` (documento assinado/upload) usa
`proposta_assinada` / `contrato_assinado` / `outros`; `DocumentoGerado.modelo.tipo` usa
`TipoDocumento` (`proposta`, `contrato`, `distrato`, ...). Precisa de um dicionário de
tradução — não são o mesmo enum. Definido em `vendas/models.py` (não dentro da view),
porque a Task 3 (management command) também precisa dele — evita duplicar o mapeamento
em dois arquivos.

**Arquivos:**
- Modificar: `vendas/models.py` (novo mapeamento módulo-level, perto de `VendaDocumento`)
- Modificar: `vendas/views/detail_views.py` (`VendaDocumentoUploadView.post`, ~L394-424)
- Test: `vendas/tests/test_detail_views.py` (classe `TestVendaDocumentoUploadView`)

**Diff conceitual — `vendas/models.py`:**

```python
# módulo, perto da classe VendaDocumento
TIPO_ASSINADO_PARA_GERADO = {
	'proposta_assinada': 'proposta',
	'contrato_assinado': 'contrato',
}
```

**Diff conceitual — `vendas/views/detail_views.py`:**

```python
# módulo, perto do topo do arquivo, junto dos outros imports de documentos
from documentos.models import StatusDocumento  # DocumentoGerado já importado
from vendas.models import RegisterVenda, VendaDocumento, TIPO_ASSINADO_PARA_GERADO


class VendaDocumentoUploadView(LoginRequiredMixin, View):

	def post(self, request, venda_uuid):
		venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
		...
		tipo = request.POST.get('tipo', 'outros')

		tipo_gerado = TIPO_ASSINADO_PARA_GERADO.get(tipo)
		documento_gerado = None
		if tipo_gerado:
			documento_gerado = (
				DocumentoGerado.objects.filter(
					venda=venda, modelo__tipo=tipo_gerado, status=StatusDocumento.FINALIZADO,
				)
				.order_by('-criado_em')
				.first()
			)

		VendaDocumento.objects.create(
			venda=venda,
			ciclo=ciclo_atual,
			tipo=tipo,
			arquivo_assinado=arquivo,
			observacao=request.POST.get('observacao', ''),
			enviado_por=request.user,
			documento_gerado=documento_gerado,   # NOVO
		)
```

**Limitação conhecida (documentar, não resolver aqui):** se a venda tiver mais de um
`DocumentoGerado` FINALIZADO do mesmo tipo (proposta regerada após rejeição, por
exemplo), o upload sempre casa com o mais recente — mesmo que o arquivo enviado
corresponda a uma versão anterior. Aceitável pro escopo atual; se virar problema real,
propor `substitui_id` explícito no form (fora deste plano).

**Testes novos:**

```python
def test_upload_vincula_documento_gerado_finalizado_mais_recente(
	self, client, admin_user, venda, settings, tmp_path
):
	settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
	settings.MEDIA_ROOT = str(tmp_path)
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	client.force_login(admin_user)
	url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
	client.post(url, {'tipo': 'proposta_assinada', 'arquivo_assinado': _fake_file()})
	novo = VendaDocumento.objects.get(venda=venda, tipo='proposta_assinada')
	assert novo.documento_gerado_id == doc_gerado.id


def test_upload_sem_documento_gerado_finalizado_deixa_campo_nulo(
	self, client, admin_user, venda, settings, tmp_path
):
	settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
	settings.MEDIA_ROOT = str(tmp_path)
	client.force_login(admin_user)
	url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
	client.post(url, {'tipo': 'proposta_assinada', 'arquivo_assinado': _fake_file()})
	novo = VendaDocumento.objects.get(venda=venda, tipo='proposta_assinada')
	assert novo.documento_gerado_id is None
```

**Testes existentes que quebram:** nenhum — `test_admin_upload_cria_documento` e os
testes de ciclo não fazem assert sobre `documento_gerado`.

**Risco de regressão:** baixo. Mudança é puramente aditiva (campo antes sempre ficava
`None`, continua podendo ficar `None`); nenhum fluxo existente depende do valor atual.

**Dependências:** nenhuma (independente de Task 1). Pode ir em produção sozinha a
qualquer momento — não ativa gate nenhum ainda.

---

## Task 3 — Backfill de vendas ativas em risco

**Arquivos:**
- Criar: `vendas/management/__init__.py` (vazio — app não tem `management/` ainda)
- Criar: `vendas/management/commands/__init__.py` (vazio)
- Criar: `vendas/management/commands/vincular_documentos_pendentes.py`
- Test: `vendas/tests/test_management_commands.py` (novo)

**Generalizado pros dois tipos assinados** (não só `proposta_assinada`): a query de risco
rodada contra o banco de dev real (ver Premissas) achou 0 casos de `contrato_assinado`
hoje, mas isso é dev, não produção, e o próprio Task 5 vai exigir `contrato_assinado`
aprovado+vinculado pra efetivar venda — sem o mesmo relatório cobrindo os dois tipos, uma
venda com contrato aprovado sem lastro trava no Task 5 sem que ninguém tenha visto isso
no relatório antes do deploy. Custo de generalizar é zero (mesmo shape de query, `--tipo`
como filtro opcional).

**Query de risco** (usa `.vigentes()` da Task 1 e `TIPO_ASSINADO_PARA_GERADO` da Task 2 —
dependências):

```python
from vendas.models import VendaDocumento, TIPO_ASSINADO_PARA_GERADO

vendas_documento_risco = (
	VendaDocumento.objects.vigentes()
	.filter(
		tipo__in=TIPO_ASSINADO_PARA_GERADO.keys(),   # proposta_assinada, contrato_assinado
		status='aprovado',
		documento_gerado__isnull=True,
	)
	.filter(venda__tipo_venda__in=['RESERVADO', 'PRE-VENDA'], venda__is_ativo=True)
	.select_related('venda', 'venda__cliente')
)
```

Nota: filtrar por `VendaDocumento` (não por `RegisterVenda` com lookups através da FK
reversa) evita o bug clássico de `.exclude()` sobre join reverso gerar condição errada
quando a venda tem múltiplos `VendaDocumento`.

**Diff conceitual — `vendas/management/commands/vincular_documentos_pendentes.py`:**

```python
from django.core.management.base import BaseCommand
from django.db import transaction

from documentos.models import DocumentoGerado, StatusDocumento
from vendas.models import VendaDocumento, TIPO_ASSINADO_PARA_GERADO


class Command(BaseCommand):
	help = (
		'Reporta VendaDocumento(status=aprovado) sem documento_gerado vinculado, tipo '
		'proposta_assinada e/ou contrato_assinado, em vendas RESERVADO/PRE-VENDA ativas. '
		'Rodar em produção ANTES do deploy do gate de contrato (Task 4) e da efetivação '
		'estendida (Task 5).'
	)

	def add_arguments(self, parser):
		parser.add_argument(
			'--tipo', choices=list(TIPO_ASSINADO_PARA_GERADO.keys()), default=None,
			help='Restringe a um tipo (proposta_assinada ou contrato_assinado). '
			     'Sem essa flag, roda os dois.',
		)
		parser.add_argument(
			'--auto-vincular', action='store_true', default=False,
			help='Tenta vincular ao DocumentoGerado FINALIZADO mais recente do tipo correspondente.',
		)
		parser.add_argument(
			'--dry-run', action='store_true', default=False,
			help='Com --auto-vincular, simula sem salvar.',
		)

	def handle(self, *args, **options):
		tipos = [options['tipo']] if options['tipo'] else list(TIPO_ASSINADO_PARA_GERADO.keys())

		docs_risco = (
			VendaDocumento.objects.vigentes()
			.filter(tipo__in=tipos, status='aprovado', documento_gerado__isnull=True)
			.filter(venda__tipo_venda__in=['RESERVADO', 'PRE-VENDA'], venda__is_ativo=True)
			.select_related('venda', 'venda__cliente')
		)

		total = docs_risco.count()
		self.stdout.write(f'{total} VendaDocumento em risco encontrados ({", ".join(tipos)}).')

		resolvidos, pendentes = 0, 0
		for doc in docs_risco:
			venda = doc.venda
			tipo_gerado = TIPO_ASSINADO_PARA_GERADO[doc.tipo]
			candidato = None
			if options['auto_vincular']:
				candidato = (
					DocumentoGerado.objects.filter(
						venda=venda, modelo__tipo=tipo_gerado, status=StatusDocumento.FINALIZADO,
					)
					.order_by('-criado_em')
					.first()
				)

			if candidato:
				resolvidos += 1
				self.stdout.write(
					f'  venda={venda.uuid} cliente={venda.cliente} tipo={doc.tipo} -> '
					f'DocumentoGerado {candidato.numero} '
					f'{"(dry-run, não salvo)" if options["dry_run"] else "(vinculado)"}'
				)
				if not options['dry_run']:
					with transaction.atomic():
						doc.documento_gerado = candidato
						doc.save(update_fields=['documento_gerado'])
			else:
				pendentes += 1
				self.stdout.write(
					f'  venda={venda.uuid} cliente={venda.cliente} tipo_venda={venda.tipo_venda} '
					f'tipo={doc.tipo} VendaDocumento#{doc.pk} -> SEM CANDIDATO, decisão manual necessária'
				)

		self.stdout.write(
			f'Total: {total} | resolvidos automaticamente: {resolvidos} | '
			f'pendentes de decisão manual: {pendentes}'
		)
```

**Testes novos:**

```python
# vendas/tests/test_management_commands.py
import pytest
from io import StringIO
from django.core.management import call_command

from vendas.models import VendaDocumento


@pytest.mark.django_db
def test_relatorio_lista_venda_em_risco_ambos_tipos(venda_pre_venda, admin_user):
	"""Sem --tipo, relatório cobre proposta_assinada E contrato_assinado."""
	VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='contrato_assinado', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/contrato.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', stdout=out)
	assert '2 VendaDocumento em risco' in out.getvalue()


@pytest.mark.django_db
def test_relatorio_filtra_por_tipo(venda_pre_venda, admin_user):
	"""Com --tipo contrato_assinado, ignora proposta_assinada em risco."""
	VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', '--tipo', 'contrato_assinado', stdout=out)
	assert '0 VendaDocumento em risco' in out.getvalue()


@pytest.mark.django_db
def test_auto_vincular_encontra_documento_gerado_finalizado(venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	call_command('vincular_documentos_pendentes', '--auto-vincular', stdout=StringIO())
	doc.refresh_from_db()
	assert doc.documento_gerado_id == doc_gerado.id


@pytest.mark.django_db
def test_auto_vincular_funciona_para_contrato_assinado(venda_pre_venda, admin_user):
	"""Mesmo fluxo, tipo=contrato_assinado -> casa com modelo__tipo='contrato'."""
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato', tipo='contrato', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Contrato',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='contrato_assinado', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/contrato.pdf',
	)
	call_command('vincular_documentos_pendentes', '--auto-vincular', stdout=StringIO())
	doc.refresh_from_db()
	assert doc.documento_gerado_id == doc_gerado.id


@pytest.mark.django_db
def test_dry_run_nao_salva(venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	call_command('vincular_documentos_pendentes', '--auto-vincular', '--dry-run', stdout=StringIO())
	doc.refresh_from_db()
	assert doc.documento_gerado_id is None
```

**Passo operacional (não é código, é execução):** depois que este PR for mergeado e
deployado, rodar em produção **antes** de deployar Task 4 (proposta) e Task 5 (proposta +
contrato) — sem `--tipo`, o comando já cobre os dois:

```bash
python manage.py vincular_documentos_pendentes            # relatório, não altera nada — cobre os 2 tipos
python manage.py vincular_documentos_pendentes --auto-vincular --dry-run   # simula backfill
python manage.py vincular_documentos_pendentes --auto-vincular            # aplica backfill automático
python manage.py vincular_documentos_pendentes            # relatório de novo — só devem sobrar os sem candidato
```

Reportar o número de casos pendentes após o auto-vincular, por tipo — esses exigem
decisão humana (gerar documento retroativo, rejeitar a aprovação, ou arquivar
manualmente) antes do gate de Task 4/5 entrar em produção.

**Testes existentes que quebram:** nenhum (código novo, sem tocar em views existentes).

**Risco de regressão:** zero em modo relatório (default). `--auto-vincular` sem
`--dry-run` escreve no banco — só rodar depois de revisar o dry-run.

**Dependências:** Task 1 (`.vigentes()`) e Task 2 (`TIPO_ASSINADO_PARA_GERADO` em
`vendas/models.py`).

---

## Task 4 — Gate de contrato (Regra 1 nova)

**Arquivos:**
- Modificar: `documentos/views_gerar.py` (`_tipos_disponiveis`, L47-56; call site L69;
  remover import `TypeLote` L20 — fica sem uso)
- Modificar: `vendas/views/detail_views.py` (`AnaliseView.get_context_data` ~L106,
  `ReservadoDetalheView.get_context_data` ~L252)
- Test: `documentos/tests/test_views_gerar.py` (classe `GerarDocumentoEtapaGateTest`)

**Diff conceitual — `documentos/views_gerar.py`:**

```python
# remove: from empreendimentos.models import TypeLote

# antes
def _tipos_disponiveis(user, situacao):
	tipos_ok = _tipos_permitidos(user)
	if situacao == TypeLote.ANALISE:
		return tipos_ok & _TIPOS_GATE_ANALISE
	return tipos_ok

# depois
def _tipos_disponiveis(user, venda):
	"""Tipos permitidos pro usuário, restritos por proposta aprovada com lastro.

	Contrato (e demais tipos além de proposta) só libera quando existe
	VendaDocumento vigente tipo=proposta_assinada, status=aprovado, com
	documento_gerado vinculado — prova que a aprovação corresponde a um
	DocumentoGerado real, não a um upload avulso. Critério NÃO depende mais
	de lote.situacao.
	"""
	tipos_ok = _tipos_permitidos(user)
	proposta_com_lastro = bool(venda) and venda.documentos_assinados.vigentes().filter(
		tipo='proposta_assinada',
		status='aprovado',
		documento_gerado__isnull=False,
	).exists()
	if not proposta_com_lastro:
		return tipos_ok & _TIPOS_GATE_ANALISE
	return tipos_ok
```

Call site (`gerar_documento`, ~L69):

```python
# antes
tipos_ok = _tipos_disponiveis(request.user, venda.lote.situacao if venda.lote else None)

# depois
tipos_ok = _tipos_disponiveis(request.user, venda)
```

`venda.documentos_assinados.vigentes()` funciona porque `vigentes()` foi definido via
`objects = VendaDocumentoQuerySet.as_manager()` — Django usa essa mesma classe de manager
pro accessor reverso da FK (`related_name='documentos_assinados'`), sem precisar de
`Meta.base_manager_name`.

**Diff conceitual — `vendas/views/detail_views.py`:**

```python
# AnaliseView.get_context_data (~L106) — venda já está em escopo (L77)
_tipos_ok = _tipos_disponiveis(self.request.user, venda)   # antes: (self.request.user, lote.situacao)

# ReservadoDetalheView.get_context_data (~L252) — venda = kwargs.get('reservas')
_tipos_ok = _tipos_disponiveis(
	self.request.user,
	venda,                                                  # antes: getattr(getattr(venda, 'lote', None), 'situacao', None)
)
```

**Testes existentes que QUEBRAM:**

`documentos/tests/test_views_gerar.py::GerarDocumentoEtapaGateTest::
test_reservado_oferece_proposta_e_contrato` — cria lote `situacao='RESERVADO'` sem
nenhum `VendaDocumento` e espera `contrato` liberado. Com o novo critério, `contrato`
fica bloqueado (não existe proposta aprovada com lastro). **Precisa reescrever:**

```python
def test_proposta_aprovada_com_lastro_libera_contrato_independente_da_situacao(self):
	"""Contrato libera quando existe proposta_assinada aprovada com documento_gerado
	vinculado — a situação do lote deixou de ser o critério (por isso ANALISE aqui,
	de propósito, não RESERVADO)."""
	from documentos.models import DocumentoGerado, StatusDocumento
	from vendas.models import VendaDocumento

	lote = _make_lote(self.quadra, situacao='ANALISE')
	venda = RegisterVenda.objects.create(lote=lote, tipo_venda='ANALISE')
	modelo_proposta = ModeloDocumento.objects.get(tipo='proposta')
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo_proposta, modelo_versao_snapshot=1, venda=venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=self.user,
	)
	VendaDocumento.objects.create(
		venda=venda, tipo='proposta_assinada', status='aprovado',
		documento_gerado=doc_gerado, enviado_por=self.user, arquivo_assinado='fake/p.pdf',
	)
	url = reverse('documentos:gerar-documento', args=[venda.pk])
	response = self.client.get(url)
	self.assertIn('contrato', response.context['modelos_por_tipo'])


def test_reservado_sem_proposta_aprovada_vinculada_nao_libera_contrato(self):
	"""Caso negativo — é exatamente o buraco que a regra antiga tinha: lote em
	RESERVADO não bastava mais que estar em ANALISE, se ninguém aprovou proposta com
	lastro. Reproduz o cenário real da venda 301 (proposta aprovada só por upload
	avulso, sem documento_gerado) e confirma que fica bloqueado."""
	from vendas.models import VendaDocumento

	lote = _make_lote(self.quadra, situacao='RESERVADO')
	venda = RegisterVenda.objects.create(lote=lote, tipo_venda='RESERVADO')
	VendaDocumento.objects.create(
		venda=venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=self.user, arquivo_assinado='fake/p.pdf',
		# documento_gerado=None — upload avulso, sem lastro, igual à venda 301
	)
	url = reverse('documentos:gerar-documento', args=[venda.pk])
	response = self.client.get(url)
	self.assertNotIn('contrato', response.context['modelos_por_tipo'])
```

`test_reservado_oferece_proposta_e_contrato` (nome antigo) é removido — substituído pelos
dois testes acima, que juntos cobrem o caso que ele testava de forma incompleta (só
verificava `situacao`, nunca testou o caso "aprovado sem lastro" que é o risco real).

Manter `test_analise_oferece_apenas_proposta` e `test_post_gerar_contrato_em_analise_bloqueado`
como estão — continuam passando (nenhum `VendaDocumento` aprovado nesses casos, gate cai
no fallback `_TIPOS_GATE_ANALISE`), mas a razão do bloqueio mudou de "lote em ANALISE"
para "sem proposta aprovada com lastro" — atualizar as docstrings desses dois testes pra
não afirmar algo que não é mais verdade (situação do lote não é mais o mecanismo, é
coincidência que o cenário de teste também não tem proposta aprovada).

`vendas/tests/test_detail_views.py` (`TestAnaliseView`, `TestReservadoDetalheView`): não
fazem assert sobre `modelos_por_tipo`/tipos disponíveis — confirmado por leitura, nenhuma
quebra.

**Risco de regressão:** médio-alto em produção (não em teste) — é o ponto exato onde o
achado da venda 301 vira bloqueio real. **Só fazer deploy depois de rodar Task 3 em
produção e revisar os pendentes.**

**Dependências:** Task 1 (`.vigentes()`). Depende operacionalmente de Task 3 ter rodado
em produção antes do deploy (não é dependência de código, é dependência de dado).

---

## Task 5 — `EfetivarVendaView` estendida

**Decisão de design:** o check de `proposta_assinada` que já existe em
`EfetivarVendaView` HOJE não verifica `documento_gerado` nem usa `.vigentes()` — é o
mesmo tipo de furo que a Task 4 fecha em `_tipos_disponiveis`. Este plano aproveita pra
aplicar o mesmo padrão (`vigente + aprovado + documento_gerado vinculado`) nos dois
checks (`proposta_assinada` E o novo `contrato_assinado`), não só no novo. Consequência:
os testes de sucesso existentes de `TestEfetivarVendaView` quebram porque a fixture atual
não vincula `documento_gerado` — ver abaixo.

**Extração de duplicação:** a lógica de checklist de documentos obrigatórios do cliente
já existe, inline, em `PreVendaDetalheView.get` (`vendas/views/detail_views.py:341-378`).
Em vez de duplicar em `EfetivarVendaView`, extrair pra `vendas/services.py` e usar nos
dois lugares — reduz ~35 linhas duplicadas pra 1 chamada de função.

**Arquivos:**
- Criar: `vendas/services.py`
- Modificar: `vendas/views/create_views.py` (`EfetivarVendaView.post`, L25-55; import L15)
- Modificar: `vendas/views/detail_views.py` (`PreVendaDetalheView.get`, L341-378 — troca
  bloco inline por chamada de serviço)
- Modificar: `vendas/tests/test_create_views.py` (fixtures de `TestEfetivarVendaView`)

**Diff conceitual — `vendas/services.py` (arquivo novo):**

```python
from clientes.models import ClienteDocumento


def checklist_documentos_cliente(cliente):
	"""Checklist de documentos obrigatórios do cliente (PF/PJ) com status de disponibilidade.

	Usado por PreVendaDetalheView (exibição) e EfetivarVendaView (gate de efetivação) —
	mesma regra de negócio, não duplicar.
	"""
	docs_cliente = ClienteDocumento.objects.filter(cliente=cliente, status='disponivel')
	tipos_disponiveis = set(docs_cliente.values_list('tipo', flat=True))
	tipo_pessoa = 'PJ' if cliente and cliente.documento and len(cliente.documento) == 14 else 'PF'

	docs_obrigatorios = []
	if tipo_pessoa == 'PF':
		if 'CNH' in tipos_disponiveis:
			docs_obrigatorios.append('CNH')
		else:
			docs_obrigatorios += ['RG', 'CPF']
		docs_obrigatorios.append('COMPROVANTE_RESIDENCIA')
		estado_civil = (cliente.estado_civil or '').lower()
		if estado_civil not in ('solteiro', 'solteira'):
			docs_obrigatorios.append('COMPROVANTE_ESTADO_CIVIL')
	else:
		docs_obrigatorios = [
			'CNPJ', 'CONTRATO_SOCIAL', 'RG_CPF_ADMINISTRADOR', 'COMPROVANTE_RESIDENCIA',
		]

	tipo_labels = dict(ClienteDocumento.TIPO_CHOICES)
	checklist = []
	for tipo in docs_obrigatorios:
		doc = docs_cliente.filter(tipo=tipo).first()
		checklist.append({
			'tipo': tipo,
			'label': tipo_labels.get(tipo, tipo),
			'doc': doc,
			'disponivel': doc is not None,
		})
	return checklist
```

**Diff conceitual — `vendas/views/detail_views.py` (`PreVendaDetalheView.get`):**

```python
# antes: L341-378, ~35 linhas de lógica inline
# depois:
from vendas.services import checklist_documentos_cliente
...
checklist_cliente = checklist_documentos_cliente(cliente)
```

Contrato do retorno é idêntico ao dict que o template `pre_venda_detalhe.html` já
consome (`tipo`, `label`, `doc`, `disponivel`) — nenhuma mudança de template necessária.

**Diff conceitual — `vendas/views/create_views.py`:**

```python
# import, L15
from ..models import RegisterVenda, VendaDocumento          # antes: só RegisterVenda
from ..services import checklist_documentos_cliente          # novo


def _documento_assinado_com_lastro(venda, tipo):
	return venda.documentos_assinados.vigentes().filter(
		tipo=tipo, status='aprovado', documento_gerado__isnull=False,
	).exists()


@method_decorator(has_permission_decorator('criarVenda'), name='dispatch')
class EfetivarVendaView(View):

	@transaction.atomic
	def post(self, request, *args, **kwargs):
		venda = get_object_or_404(RegisterVenda, uuid=kwargs.get('venda_uuid'))
		lote = venda.lote
		empreendimento = lote.quadra.empr

		if request.user.tipo_usuario != 'ADMINISTRADOR':
			messages.error(request, "Apenas administradores podem efetivar vendas.")
			return redirect('pre-venda-detalhe', venda_uuid=venda.uuid)

		if not _documento_assinado_com_lastro(venda, 'proposta_assinada'):
			messages.error(
				request,
				"Venda não pode ser efetivada sem proposta aprovada vinculada a um documento gerado.",
			)
			return redirect('pre-venda-detalhe', venda_uuid=venda.uuid)

		if not _documento_assinado_com_lastro(venda, 'contrato_assinado'):
			messages.error(
				request,
				"Venda não pode ser efetivada sem contrato assinado aprovado vinculado a um documento gerado.",
			)
			return redirect('pre-venda-detalhe', venda_uuid=venda.uuid)

		checklist = checklist_documentos_cliente(venda.cliente)
		if not all(item['disponivel'] for item in checklist):
			messages.error(
				request,
				"Venda não pode ser efetivada: checklist de documentos do cliente incompleto.",
			)
			return redirect('pre-venda-detalhe', venda_uuid=venda.uuid)

		venda.dt_venda = timezone.localdate()
		venda.tipo_venda = 'VENDIDO'
		venda.save(update_fields=['dt_venda', 'tipo_venda'])

		lote.situacao = 'VENDIDO'
		lote.save(update_fields=['situacao'])

		messages.success(request, "Venda efetivada com sucesso!")
		return redirect('listar-quadras', empreendimento_uuid=empreendimento.uuid)
```

**Testes existentes que QUEBRAM — `vendas/tests/test_create_views.py::TestEfetivarVendaView`:**

A fixture `proposta_aprovada` cria `VendaDocumento` sem `documento_gerado`. Com o check
tightened, `test_post_seta_venda_vendido`, `test_post_seta_lote_vendido` e
`test_dt_venda_preenchida_apos_efetivar` param nessa fixture e vão falhar (venda não
efetiva mais). `test_nao_administrador_e_redirecionado` e
`test_sem_proposta_aprovada_nao_efetiva` continuam passando sem mudança (bloqueiam antes
de chegar nos novos checks). **Reescrever fixtures:**

```python
@pytest.fixture
def documento_gerado_finalizado(db, venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta Padrão', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	return DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)


@pytest.fixture
def contrato_gerado_finalizado(db, venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Padrão', tipo='contrato', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	return DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Contrato',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)


class TestEfetivarVendaView:

	@pytest.fixture
	def proposta_aprovada(self, venda_pre_venda, admin_user, documento_gerado_finalizado):
		return VendaDocumento.objects.create(
			venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
			documento_gerado=documento_gerado_finalizado,          # NOVO
		)

	@pytest.fixture
	def contrato_aprovado(self, venda_pre_venda, admin_user, contrato_gerado_finalizado):
		return VendaDocumento.objects.create(
			venda=venda_pre_venda, tipo='contrato_assinado', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/contrato.pdf',
			documento_gerado=contrato_gerado_finalizado,
		)

	@pytest.fixture
	def checklist_cliente_completo(self, venda_pre_venda):
		from clientes.models import ClienteDocumento
		ClienteDocumento.objects.create(
			cliente=venda_pre_venda.cliente, tipo='CNH', arquivo='fake/cnh.pdf', status='disponivel',
		)
		ClienteDocumento.objects.create(
			cliente=venda_pre_venda.cliente, tipo='COMPROVANTE_RESIDENCIA',
			arquivo='fake/comp.pdf', status='disponivel',
		)
		# cliente_pf (conftest) tem estado_civil='solteiro' — COMPROVANTE_ESTADO_CIVIL não obrigatório

	def test_post_seta_venda_vendido(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda == 'VENDIDO'

	# idem para test_post_seta_lote_vendido e test_dt_venda_preenchida_apos_efetivar:
	# adicionar contrato_aprovado e checklist_cliente_completo aos parâmetros.

	def test_sem_contrato_aprovado_nao_efetiva(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, checklist_cliente_completo,
	):
		"""Só proposta aprovada, sem contrato — não efetiva."""
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

	def test_checklist_incompleto_nao_efetiva(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, contrato_aprovado,
	):
		"""Proposta e contrato aprovados, mas checklist do cliente incompleto — não efetiva."""
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

	def test_proposta_aprovada_sem_documento_gerado_nao_efetiva(
		self, client, admin_user, venda_pre_venda,
	):
		"""proposta_assinada aprovado SEM documento_gerado vinculado (caso venda 301) — bloqueia."""
		VendaDocumento.objects.create(
			venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
			# documento_gerado=None — de propósito
		)
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'
```

**Testes existentes que quebram em `PreVendaDetalheView` (checklist):** nenhum —
`checklist_documentos_cliente()` reproduz exatamente a mesma lógica linha por linha, os
testes `test_checklist_pf_*` e `test_checklist_pj_*` continuam passando sem alteração
(dependem só do formato do dict retornado, que não muda).

**Risco de regressão:** alto em produção — este é o segundo ponto onde vendas
PRE-VENDA existentes sem `contrato_assinado` aprovado (a maioria, provavelmente, já que
esse check nunca existiu antes) ficam impedidas de efetivar até anexar/aprovar o
contrato. Isso é uma mudança de regra de negócio real, não só um bugfix — **validar com
o time de negócio antes do deploy**, não só com Task 3 (que cobre só o caso da proposta,
não do contrato).

**Dependências:** Task 1 (`.vigentes()`), Task 3 já generalizada pros dois tipos (ver
Task 3) — não precisa de segunda rodada de comando, o mesmo relatório sem `--tipo` já
cobre `contrato_assinado`. Query real rodada em 2026-07-02 contra o banco de dev
(`glot_teste@172.16.51.3`) achou **0 casos** de `contrato_assinado` aprovado sem
`documento_gerado` em vendas RESERVADO/PRE-VENDA ativas — bem diferente do achado de
`proposta_assinada` (1 caso, venda 301). **Isso é dev, não produção.** Antes do deploy de
Task 5, rodar `python manage.py vincular_documentos_pendentes --tipo contrato_assinado`
em produção e confirmar que o número também é baixo o suficiente pra não travar um volume
grande de vendas de uma vez — se produção tiver muito mais `contrato_assinado` aprovado
sem lastro do que dev (plausível, já que esse check nunca existiu antes desta task),
`--auto-vincular` reduz o problema mas os casos "sem candidato" ainda exigem decisão
humana antes do deploy.

---

## Ordem de execução e agrupamento de PR

| Task | Depende de | Risco em prod | PR |
|---|---|---|---|
| 1 — manager `vigentes()` | — | baixo nas 3 leituras, **médio no `CancelarReservaView`** (arquiva `rejeitado` agora — mudança deliberada, exige o teste novo) | PR próprio, mergear primeiro, com o teste de `rejeitado` incluído |
| 2 — auto-link no upload | — | baixo (aditivo) | PR próprio, pode ir junto ou depois de 1 |
| 3 — backfill command (2 tipos) | 1, 2 | zero (modo relatório) | PR próprio, mergear e RODAR EM PROD (sem `--tipo`, cobre os 2) antes de 4/5 |
| 4 — gate de contrato | 1, dado de 3 (proposta) | médio-alto | — |
| 5 — EfetivarVendaView | 1, dado de 3 (proposta E contrato — mesmo comando) | alto | — |

**Recomendação:** Tasks 1, 2 e 3 são independentes entre si — três PRs pequenos, mas Task
1 não é "baixíssimo risco" sem qualificação: o comportamento novo do
`CancelarReservaView` (arquivar `rejeitado`) precisa do teste dedicado revisado antes de
aprovar esse PR especificamente; Tasks 2 e 3 seguem baixo risco sem ressalva. Depois de
Task 3 rodar em produção (relatório único cobrindo proposta E contrato, revisado e com os
pendentes resolvidos ou triados), Tasks 4 e 5 devem ir **juntas num mesmo PR/deploy** —
são as duas metades do mesmo gate de negócio (gerar contrato / efetivar venda) e
deployar uma sem a outra deixa o sistema num estado inconsistente (ex: consegue gerar
contrato mas trava ao efetivar por um motivo que ninguém sinalizou na tela de geração).
Avisar o time de negócio antes desse deploy — é a única dupla de tasks que muda regra de
aprovação de venda de verdade, e a real extensão do impacto em produção (quantas vendas
PRE-VENDA hoje têm contrato aprovado sem lastro) só se sabe depois de rodar Task 3 lá,
não em dev.