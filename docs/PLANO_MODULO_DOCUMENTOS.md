# GLOT — Reestruturação Completa do App `documentos`

> **Instruções para o Claude Code:** Este documento é o plano de implementação completo do novo módulo de documentos do GLOT. Execute as fases NA ORDEM. Cada fase tem critérios de aceite. Não pule fases. Todas as decisões arquiteturais já foram tomadas — não pergunte sobre alternativas, apenas implemente conforme especificado. Siga as convenções do projeto: tabs para indentação, snake_case em Python, camelCase em JS.

---

## 0. Contexto e decisões tomadas

### O que é
Módulo de geração de documentos jurídicos imobiliários (contratos, distratos, propostas, termos de reserva, recibos, declarações, termos aditivos, notificações) a partir de **modelos reutilizáveis com variáveis**, preenchidos automaticamente com dados do sistema (cliente, venda, lote, quadra, empreendimento).

### Decisões fechadas (NÃO reabrir)

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | App documentos | **Apagar o app atual e reestruturar do zero** (manter backup dos templates HTML existentes antes de apagar) |
| 2 | Celery + Redis | **Reestruturar/configurar** como parte deste plano (Fase 1) |
| 3 | Editor | **TipTap vendorizado nos staticfiles** (sem CDN, sem NPM em produção — bundle commitado no repo, servido via collectstatic). Produção roda em stack Docker Swarm via Portainer |
| 4 | Storage | **media/ local por enquanto** (VPS Hetzner). Estruturar o código com `default_storage` do Django para facilitar migração futura para S3/MinIO |
| 5 | Distrato → lote | Lote volta para **DISPONÍVEL** imediatamente na confirmação do distrato |
| 6 | Aprovação | **Não há fluxo de aprovação.** Vendedor gera e finaliza sozinho (contratos e distratos) |
| 7 | Numeração | **Automática por tipo + ano**, formato `CTR-2025-0042`. Sequência zera a cada ano. Prefixos por tipo (ver tabela abaixo) |
| 8 | Correção de documento | **SEMPRE gera um novo documento.** O anterior recebe status SUBSTITUIDO. Nunca editar documento finalizado — histórico jurídico completo |
| 9 | PDF | **WeasyPrint via Celery task** |
| 10 | Word (.docx) | **Fase futura (não implementar agora).** Deixar campo `arquivo_word` no model preparado |
| 11 | Variáveis | **Globais** (mesma variável serve para qualquer documento), armazenadas na tabela `VariavelDocumento`, inseridas como **nó atômico** no TipTap |
| 12 | Renderização | Django Template Engine **restrito** (`builtins` limpos) + validação allowlist antes de salvar modelo |
| 13 | Cabeçalho/rodapé | Separados do modelo, em `ConfiguracaoDocumento` (OneToOne com Empreendimento): logo, HTML de cabeçalho/rodapé, margens, fonte |
| 14 | Vínculo empreendimento ↔ modelo | Tabela `EmpreendimentoDocumento` (M2M com metadados: `padrao`, `ativo`, `ordem`). Modelos podem ser `eh_global=True` (disponíveis para todos) |
| 15 | Imutabilidade | `DocumentoGerado` com `status=FINALIZADO` bloqueia alteração de conteúdo via `save()`. `hash_conteudo` SHA-256 para auditoria |
| 16 | ONLYOFFICE / assinatura digital | **Fora do escopo.** Não implementar, não preparar stubs |

### Prefixos de numeração por tipo

| Tipo | Prefixo |
|------|---------|
| contrato | CTR |
| distrato | DST |
| proposta | PRP |
| reserva | RSV |
| declaracao | DCL |
| recibo | RCB |
| termo_aditivo | TAD |
| notificacao | NTF |
| outros | DOC |

---

## FASE 0 — Backup e demolição

1. **Backup**: copiar todo o conteúdo atual de `apps/documentos/` (ou onde estiver o app atual) para `_backup/documentos_legado/` na raiz do projeto. Incluir especialmente os templates HTML de documentos existentes (ex: Proposta de Compra e Venda) — eles serão a base do conteúdo dos primeiros `ModeloDocumento` via data migration.
2. **Exportar dados**: se existirem registros nas tabelas atuais do app documentos, fazer `dumpdata` para `_backup/documentos_dados.json`.
3. **Remover**: apagar o app `documentos` de `INSTALLED_APPS`, gerar migration de remoção das tabelas antigas (ou drop manual documentado), apagar o diretório do app.
4. **Recriar**: `python manage.py startapp documentos` dentro de `apps/`.

**Critério de aceite:** projeto sobe sem erros com o app novo vazio registrado em `INSTALLED_APPS`.

---

## FASE 1 — Infraestrutura: Celery + Redis

Reestruturar o Celery do zero:

1. **Redis** no `docker-compose`/stack do Portainer:
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
  deploy:
    resources:
      limits:
        memory: 256M
```

2. **Celery app** em `config/celery.py` (ou `glot/celery.py` conforme estrutura do projeto):
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('glot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

3. **Settings:**
```python
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 90
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

4. **Serviço worker** na stack:
```yaml
celery-worker:
  image: davidnobrega/glot:latest
  command: celery -A config worker -l info --concurrency=2
  environment: *glot-env   # mesmas envs do serviço web
  depends_on: [redis, postgres]
```

5. **Dockerfile**: garantir que o WeasyPrint instala (dependências de sistema):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
```
E no `requirements.txt`: `celery[redis]>=5.3`, `weasyprint>=60`, `num2words`.

**Critério de aceite:** task de teste `debug_task.delay()` executa no worker e retorna sucesso. WeasyPrint importa sem erro no container.

---

## FASE 2 — Models

Criar em `apps/documentos/models.py`. Todos os models com `criado_em`/`atualizado_em` onde fizer sentido.

### 2.1 TipoDocumento (choices como TextChoices)
```python
class TipoDocumento(models.TextChoices):
	CONTRATO = 'contrato', 'Contrato'
	DISTRATO = 'distrato', 'Distrato'
	PROPOSTA = 'proposta', 'Proposta'
	RESERVA = 'reserva', 'Reserva'
	DECLARACAO = 'declaracao', 'Declaração'
	RECIBO = 'recibo', 'Recibo'
	TERMO_ADITIVO = 'termo_aditivo', 'Termo Aditivo'
	NOTIFICACAO = 'notificacao', 'Notificação'
	OUTROS = 'outros', 'Outros'

PREFIXO_POR_TIPO = {
	'contrato': 'CTR', 'distrato': 'DST', 'proposta': 'PRP',
	'reserva': 'RSV', 'declaracao': 'DCL', 'recibo': 'RCB',
	'termo_aditivo': 'TAD', 'notificacao': 'NTF', 'outros': 'DOC',
}
```

### 2.2 VariavelDocumento
```python
class VariavelDocumento(models.Model):
	CATEGORIAS = [
		('cliente', 'Cliente'), ('conjuge', 'Cônjuge'),
		('empreendimento', 'Empreendimento'), ('lote', 'Lote / Quadra'),
		('venda', 'Venda'), ('distrato', 'Distrato'), ('sistema', 'Sistema'),
	]
	categoria = models.CharField(max_length=30, choices=CATEGORIAS)
	tag_slug = models.CharField(max_length=100, unique=True)   # "cliente.nome"
	label = models.CharField(max_length=100)                    # "Nome completo"
	exemplo = models.CharField(max_length=200, blank=True)      # "João da Silva"
	ativo = models.BooleanField(default=True)
	ordem = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['categoria', 'ordem', 'label']

	@property
	def tag(self):
		return '{{ %s }}' % self.tag_slug
```

### 2.3 ModeloDocumento
```python
class ModeloDocumento(models.Model):
	titulo = models.CharField(max_length=255)
	tipo = models.CharField(max_length=30, choices=TipoDocumento.choices)
	conteudo_html = models.TextField(blank=True)
	eh_global = models.BooleanField(default=False)  # disponível p/ todos empreendimentos
	versao = models.PositiveIntegerField(default=1)
	ativo = models.BooleanField(default=True)
	criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	objects = ModeloDocumentoManager()
```
- Sobrescrever `save()`: se `conteudo_html` mudou em update, incrementa `versao` e cria `ModeloDocumentoHistorico` (snapshot do conteúdo anterior).
- **Sem FK para empreendimento** — vínculo via tabela abaixo.

### 2.4 EmpreendimentoDocumento
```python
class EmpreendimentoDocumento(models.Model):
	empreendimento = models.ForeignKey('empreendimentos.Empreendimento', on_delete=models.CASCADE, related_name='documentos_config')
	modelo = models.ForeignKey(ModeloDocumento, on_delete=models.PROTECT, related_name='empreendimentos_vinculo')
	padrao = models.BooleanField(default=False)
	ativo = models.BooleanField(default=True)
	ordem = models.PositiveSmallIntegerField(default=0)

	class Meta:
		unique_together = ('empreendimento', 'modelo')
		ordering = ['modelo__tipo', 'ordem']

	def clean(self):
		# Apenas UM padrão por tipo por empreendimento
		if self.padrao:
			conflito = EmpreendimentoDocumento.objects.filter(
				empreendimento=self.empreendimento,
				modelo__tipo=self.modelo.tipo,
				padrao=True,
			).exclude(pk=self.pk)
			if conflito.exists():
				raise ValidationError('Já existe um modelo padrão deste tipo para este empreendimento.')
```

### 2.5 ModeloDocumentoManager
```python
class ModeloDocumentoManager(models.Manager):
	def para_empreendimento(self, empreendimento, tipo=None):
		vinculos = EmpreendimentoDocumento.objects.filter(
			empreendimento=empreendimento, ativo=True,
		).values_list('modelo_id', flat=True)
		qs = self.filter(
			models.Q(id__in=list(vinculos)) | models.Q(eh_global=True),
			ativo=True,
		)
		if tipo:
			qs = qs.filter(tipo=tipo)
		return qs.distinct()

	def padrao_para(self, empreendimento, tipo):
		vinculo = EmpreendimentoDocumento.objects.filter(
			empreendimento=empreendimento, modelo__tipo=tipo,
			padrao=True, ativo=True,
		).select_related('modelo').first()
		if vinculo:
			return vinculo.modelo
		return self.filter(tipo=tipo, eh_global=True, ativo=True).first()
```

### 2.6 ConfiguracaoDocumento
```python
class ConfiguracaoDocumento(models.Model):
	empreendimento = models.OneToOneField('empreendimentos.Empreendimento', on_delete=models.CASCADE, related_name='config_documento')
	logo = models.ImageField(upload_to='documentos/logos/', null=True, blank=True)
	logo_largura = models.PositiveSmallIntegerField(default=120)
	cabecalho_html = models.TextField(blank=True)
	rodape_html = models.TextField(blank=True)
	margem_sup = models.PositiveSmallIntegerField(default=25)
	margem_inf = models.PositiveSmallIntegerField(default=20)
	margem_esq = models.PositiveSmallIntegerField(default=30)
	margem_dir = models.PositiveSmallIntegerField(default=20)
	fonte_familia = models.CharField(max_length=50, default='Times New Roman')
	fonte_tamanho = models.PositiveSmallIntegerField(default=12)
```

### 2.7 DocumentoGerado
```python
class StatusDocumento(models.TextChoices):
	RASCUNHO = 'rascunho', 'Rascunho'
	PROCESSANDO = 'processando', 'Processando'   # Celery gerando PDF
	FINALIZADO = 'finalizado', 'Finalizado'
	CANCELADO = 'cancelado', 'Cancelado'
	SUBSTITUIDO = 'substituido', 'Substituído'

class DocumentoGerado(models.Model):
	numero = models.CharField(max_length=20, unique=True, editable=False)  # CTR-2025-0042
	modelo = models.ForeignKey(ModeloDocumento, on_delete=models.PROTECT)
	modelo_versao_snapshot = models.PositiveIntegerField()
	venda = models.ForeignKey('vendas.RegisterVenda', on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
	cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
	distrato = models.ForeignKey('documentos.Distrato', on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
	titulo = models.CharField(max_length=255)
	conteudo_final_html = models.TextField()
	status = models.CharField(max_length=20, choices=StatusDocumento.choices, default=StatusDocumento.RASCUNHO)
	hash_conteudo = models.CharField(max_length=64, blank=True)  # SHA-256
	arquivo_pdf = models.FileField(upload_to='documentos/pdf/%Y/%m/', null=True, blank=True)
	arquivo_word = models.FileField(upload_to='documentos/word/%Y/%m/', null=True, blank=True)  # fase futura
	substitui = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='substituido_por')
	criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	criado_em = models.DateTimeField(auto_now_add=True)
	finalizado_em = models.DateTimeField(null=True, blank=True)
```
Regras no `save()`:
- Em criação: gerar `numero` via `SequencialDocumento` (abaixo) — dentro de `transaction.atomic()` + `select_for_update`.
- Se já existe no banco com `status=FINALIZADO`: bloquear alteração de `conteudo_final_html`, `numero`, `modelo`, `venda` (levantar `ValidationError`). Permitir apenas mudança de status para `SUBSTITUIDO` ou `CANCELADO`.
- Ao finalizar: calcular `hash_conteudo = sha256(conteudo_final_html)`, setar `finalizado_em`.

### 2.8 SequencialDocumento (numeração por tipo+ano)
```python
class SequencialDocumento(models.Model):
	tipo = models.CharField(max_length=30)
	ano = models.PositiveSmallIntegerField()
	ultimo = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = ('tipo', 'ano')

	@classmethod
	def proximo_numero(cls, tipo):
		"""Gera CTR-2025-0042. Chamar SEMPRE dentro de transaction.atomic()."""
		ano = timezone.now().year
		seq, _ = cls.objects.select_for_update().get_or_create(tipo=tipo, ano=ano)
		seq.ultimo += 1
		seq.save(update_fields=['ultimo'])
		prefixo = PREFIXO_POR_TIPO.get(tipo, 'DOC')
		return f'{prefixo}-{ano}-{seq.ultimo:04d}'
```

### 2.9 Distrato
```python
class Distrato(models.Model):
	class Status(models.TextChoices):
		RASCUNHO = 'rascunho', 'Rascunho'
		CONCLUIDO = 'concluido', 'Concluído'

	venda = models.ForeignKey('vendas.RegisterVenda', on_delete=models.PROTECT, related_name='distratos')
	cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='+')
	motivo = models.TextField()
	data_distrato = models.DateField()
	valor_devolucao = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	percentual_retencao = models.DecimalField(max_digits=5, decimal_places=2, default=0)
	observacao = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
	criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	criado_em = models.DateTimeField(auto_now_add=True)
	concluido_em = models.DateTimeField(null=True, blank=True)
```

### 2.10 ModeloDocumentoHistorico
```python
class ModeloDocumentoHistorico(models.Model):
	modelo = models.ForeignKey(ModeloDocumento, on_delete=models.CASCADE, related_name='historico')
	versao = models.PositiveIntegerField()
	conteudo_html = models.TextField()
	editado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	editado_em = models.DateTimeField(auto_now_add=True)
```

**Ajustar nomes de FKs** (`vendas.RegisterVenda`, `clientes.Cliente`, `empreendimentos.Empreendimento`) conforme os apps/models reais do GLOT — verificar antes de gerar migrations.

**Critério de aceite:** `makemigrations` + `migrate` sem erros. Admin registrado para todos os models (list_display, search, filters básicos).

---

## FASE 3 — Data migration: variáveis globais

Criar data migration populando `VariavelDocumento` com TODAS as variáveis abaixo. O `tag_slug` deve corresponder exatamente às chaves geradas pelo `montar_contexto_*` (Fase 4).

| categoria | tag_slug | label | exemplo |
|---|---|---|---|
| cliente | cliente.nome | Nome completo | João da Silva |
| cliente | cliente.cpf | CPF (sem formatação) | 12345678900 |
| cliente | cliente.cpf_formatado | CPF formatado | 123.456.789-00 |
| cliente | cliente.rg | RG | 2001234567 |
| cliente | cliente.estado_civil | Estado civil | Casado |
| cliente | cliente.profissao | Profissão | Engenheiro |
| cliente | cliente.nacionalidade | Nacionalidade | Brasileiro |
| cliente | cliente.naturalidade | Naturalidade | Juazeiro do Norte/CE |
| cliente | cliente.endereco_completo | Endereço completo | Rua A, 123, Centro, Juazeiro do Norte/CE, CEP 63000-000 |
| cliente | cliente.telefone | Telefone principal | (88) 99999-0000 |
| cliente | cliente.email | E-mail | joao@email.com |
| conjuge | conjuge.nome | Nome do cônjuge | Maria da Silva |
| conjuge | conjuge.cpf_formatado | CPF do cônjuge | 987.654.321-00 |
| conjuge | conjuge.rg | RG do cônjuge | 2007654321 |
| conjuge | conjuge.profissao | Profissão do cônjuge | Professora |
| conjuge | conjuge.nacionalidade | Nacionalidade do cônjuge | Brasileira |
| empreendimento | empreendimento.nome | Nome do empreendimento | Residencial das Flores |
| empreendimento | empreendimento.razao_social | Razão social | Flores Empreendimentos LTDA |
| empreendimento | empreendimento.cnpj_formatado | CNPJ formatado | 12.345.678/0001-99 |
| empreendimento | empreendimento.matricula | Matrícula do imóvel | 45.678 |
| empreendimento | empreendimento.endereco | Endereço | Av. Principal, s/n |
| empreendimento | empreendimento.cidade | Cidade | Juazeiro do Norte |
| empreendimento | empreendimento.estado | Estado (UF) | CE |
| lote | quadra.nome | Quadra | Quadra 05 |
| lote | lote.numero | Número do lote | 12 |
| lote | lote.area_formatada | Área (m²) | 250,00 |
| lote | lote.valor_formatado | Valor do lote (R$) | R$ 45.000,00 |
| venda | venda.numero | Código da venda | 2047 |
| venda | venda.valor_total | Valor total (R$) | R$ 45.000,00 |
| venda | venda.valor_total_extenso | Valor total por extenso | quarenta e cinco mil reais |
| venda | venda.valor_entrada | Valor de entrada | R$ 5.000,00 |
| venda | venda.valor_entrada_extenso | Entrada por extenso | cinco mil reais |
| venda | venda.qtd_parcelas | Quantidade de parcelas | 120 |
| venda | venda.valor_parcela | Valor da parcela | R$ 333,33 |
| venda | venda.valor_parcela_extenso | Parcela por extenso | trezentos e trinta e três reais e trinta e três centavos |
| venda | venda.data_venda | Data da venda | 10/06/2026 |
| venda | venda.data_venda_extenso | Data por extenso | 10 de junho de 2026 |
| venda | venda.forma_pagamento | Forma de pagamento | Parcelado |
| distrato | distrato.motivo | Motivo do distrato | Inadimplência |
| distrato | distrato.data_distrato | Data do distrato | 10/06/2026 |
| distrato | distrato.data_extenso | Data por extenso | 10 de junho de 2026 |
| distrato | distrato.valor_devolucao | Valor de devolução | R$ 3.500,00 |
| distrato | distrato.valor_extenso | Devolução por extenso | três mil e quinhentos reais |
| distrato | distrato.percentual_retencao | % de retenção | 30 |
| sistema | sistema.data_hoje | Data atual | 10/06/2026 |
| sistema | sistema.data_hoje_extenso | Data atual por extenso | 10 de junho de 2026 |
| sistema | sistema.cidade_estado | Cidade/UF do empreendimento | Juazeiro do Norte/CE |
| sistema | usuario.nome | Usuário que gerou | Ana Lima |

**Critério de aceite:** migration roda, ~48 variáveis no banco, visíveis no admin.

---

## FASE 4 — Services (núcleo do módulo)

Criar `apps/documentos/services.py`. Toda lógica de negócio aqui — views ficam finas.

### 4.1 Contextos
```python
from num2words import num2words

def _moeda(valor):
	return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def _extenso_moeda(valor):
	return num2words(valor, lang='pt_BR', to='currency')

def _data_br(d):
	return d.strftime('%d/%m/%Y') if d else ''

def _data_extenso(d):
	MESES = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
	return f'{d.day} de {MESES[d.month-1]} de {d.year}' if d else ''
```

`montar_contexto_venda(venda, usuario)` retorna dict **plano** (não objetos!) com TODAS as chaves de venda/cliente/conjuge/lote/quadra/empreendimento/sistema da tabela da Fase 3, já formatadas. Campos de cônjuge: se cliente não tiver cônjuge, retornar strings vazias (nunca quebrar).

`montar_contexto_distrato(distrato, usuario)` = contexto da venda + chaves `distrato.*`.

> **IMPORTANTE**: o contexto entrega valores prontos (strings formatadas), nunca objetos do ORM. Isso elimina acesso arbitrário a atributos via template (segurança) e garante formatação consistente.
> Como as chaves têm pontos (`cliente.nome`), montar o contexto como dicts aninhados: `{'cliente': {'nome': ..., 'cpf': ...}, 'venda': {...}}`.

### 4.2 Renderização segura
```python
from django.template import Engine, Context

_engine_seguro = Engine(
	debug=False,
	libraries={},
	builtins=['django.template.defaulttags'],  # apenas if/for básicos; SEM load, SEM include
	string_if_invalid='[VARIÁVEL INVÁLIDA: %s]',
	autoescape=False,
)

def renderizar_variaveis(conteudo_html, contexto):
	template = _engine_seguro.from_string(conteudo_html)
	return template.render(Context(contexto))
```

### 4.3 Validação de variáveis (antes de salvar modelo)
```python
import re

RE_VARIAVEL = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
RE_TAG_PROIBIDA = re.compile(r'\{%')

def validar_conteudo_modelo(conteudo_html):
	"""Retorna lista de erros. Vazia = OK."""
	erros = []
	if RE_TAG_PROIBIDA.search(conteudo_html):
		erros.append('Tags de template ({% %}) não são permitidas.')
	usadas = set(RE_VARIAVEL.findall(conteudo_html))
	permitidas = set(VariavelDocumento.objects.filter(ativo=True).values_list('tag_slug', flat=True))
	invalidas = usadas - permitidas
	if invalidas:
		erros.append(f'Variáveis inválidas: {", ".join(sorted(invalidas))}')
	return erros
```

### 4.4 Geração de documento
```python
def gerar_documento_venda(venda, tipo, usuario, modelo_id=None, substitui_id=None):
	"""
	Cria DocumentoGerado (RASCUNHO) para uma venda.
	- modelo_id None → usa padrão do empreendimento (padrao_para)
	- substitui_id → marca o documento anterior como SUBSTITUIDO (regra: sempre gera novo)
	"""
	empreendimento = venda.lote.quadra.empreendimento  # ajustar path conforme models reais

	with transaction.atomic():
		if modelo_id:
			modelo = ModeloDocumento.objects.get(pk=modelo_id)
			# validar disponibilidade p/ empreendimento (vinculado OU global)
		else:
			modelo = ModeloDocumento.objects.padrao_para(empreendimento, tipo)
			if not modelo:
				raise ValidationError(f'Nenhum modelo padrão de {tipo} configurado para {empreendimento}.')

		contexto = montar_contexto_venda(venda, usuario)
		html_final = renderizar_variaveis(modelo.conteudo_html, contexto)

		doc = DocumentoGerado(
			numero=SequencialDocumento.proximo_numero(modelo.tipo),
			modelo=modelo,
			modelo_versao_snapshot=modelo.versao,
			venda=venda,
			cliente=venda.cliente,
			titulo=f'{modelo.titulo} — {venda.cliente}',
			conteudo_final_html=html_final,
			status=StatusDocumento.RASCUNHO,
			criado_por=usuario,
		)
		doc.save()

		if substitui_id:
			anterior = DocumentoGerado.objects.select_for_update().get(pk=substitui_id)
			anterior.status = StatusDocumento.SUBSTITUIDO
			anterior.save(update_fields=['status'])
			doc.substitui = anterior
			doc.save(update_fields=['substitui'])

	return doc
```

### 4.5 Finalizar documento (dispara PDF)
```python
def finalizar_documento(doc, usuario):
	if doc.status != StatusDocumento.RASCUNHO:
		raise ValidationError('Apenas rascunhos podem ser finalizados.')
	doc.status = StatusDocumento.PROCESSANDO
	doc.hash_conteudo = hashlib.sha256(doc.conteudo_final_html.encode()).hexdigest()
	doc.save(update_fields=['status', 'hash_conteudo'])
	from .tasks import gerar_pdf_documento
	gerar_pdf_documento.delay(doc.pk)
	return doc
```

### 4.6 Concluir distrato (regra de negócio crítica)
```python
def concluir_distrato(distrato, usuario):
	"""
	Conclui o distrato de forma ATÔMICA:
	1. Exige documento de distrato FINALIZADO vinculado
	2. Venda → status DISTRATADA
	3. Lote → status DISPONIVEL (decisão #5)
	4. Distrato → CONCLUIDO
	"""
	with transaction.atomic():
		venda = RegisterVenda.objects.select_for_update().get(pk=distrato.venda_id)
		lote = Lote.objects.select_for_update().get(pk=venda.lote_id)

		tem_doc = distrato.documentos.filter(status=StatusDocumento.FINALIZADO).exists()
		if not tem_doc:
			raise ValidationError('É necessário finalizar o documento de distrato antes de concluir.')

		venda.status = 'distratada'      # ajustar ao choices real do model de venda
		venda.save(update_fields=['status'])

		lote.situacao = 'disponivel'     # ajustar ao choices real do model de lote
		lote.save(update_fields=['situacao'])

		distrato.status = Distrato.Status.CONCLUIDO
		distrato.concluido_em = timezone.now()
		distrato.save(update_fields=['status', 'concluido_em'])
	return distrato
```

> Verificar os nomes reais dos campos/choices de status em `RegisterVenda` e `Lote` antes de implementar.

### 4.7 Duplicar modelo
Conforme planejado: cópia com `titulo + ' (cópia)'`, `versao=1`, vínculos de empreendimento copiados com `padrao=False, ativo=False`.

**Critério de aceite:** testes unitários (pytest-django) cobrindo: renderização segura (incluindo bloqueio de `{% %}`), validação de variáveis, numeração sequencial com concorrência, imutabilidade do FINALIZADO, distrato atômico (rollback se falhar no meio).

---

## FASE 5 — Task Celery: geração de PDF

`apps/documentos/tasks.py`:

```python
from celery import shared_task
from weasyprint import HTML, CSS
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def gerar_pdf_documento(self, documento_id):
	doc = DocumentoGerado.objects.select_related('modelo', 'venda').get(pk=documento_id)
	try:
		empreendimento = doc.venda.lote.quadra.empreendimento if doc.venda else None
		cfg = getattr(empreendimento, 'config_documento', None) if empreendimento else None

		html_str = render_to_string('documentos/pdf/documento_base.html', {
			'doc': doc,
			'cfg': cfg,
		})
		css = CSS(filename=finders.find('documentos/css/documento_a4.css'))
		pdf_bytes = HTML(string=html_str, base_url=settings.MEDIA_ROOT).write_pdf(stylesheets=[css])

		doc.arquivo_pdf.save(f'{doc.numero}.pdf', ContentFile(pdf_bytes), save=False)
		doc.status = StatusDocumento.FINALIZADO
		doc.finalizado_em = timezone.now()
		doc.save()
	except Exception as exc:
		doc.status = StatusDocumento.RASCUNHO  # volta para permitir retry manual
		doc.save(update_fields=['status'])
		raise self.retry(exc=exc)
```

`base_url=settings.MEDIA_ROOT` é necessário para o WeasyPrint resolver o logo do cabeçalho.

**Endpoint de polling**: `GET /documentos/<pk>/status/` retorna JSON `{status, pdf_url}`. O front faz polling a cada 2s enquanto `status == 'processando'`.

**Critério de aceite:** finalizar um documento gera PDF válido em `media/documentos/pdf/YYYY/MM/CTR-2025-0001.pdf` com cabeçalho/rodapé do empreendimento.

---

## FASE 6 — Template base do PDF + CSS A4

### `templates/documentos/pdf/documento_base.html`
HTML completo com `@page` A4, margens vindas de `cfg` (defaults se `cfg` for None), cabeçalho com `position: running(cabecalho)` e rodapé com `running(rodape)`, numeração `counter(page) / counter(pages)`. Conteúdo: `{{ doc.conteudo_final_html|safe }}`.

### `static/documentos/css/documento_a4.css`
CSS compartilhado entre o editor (simulação visual) e o WeasyPrint:
- `.editor-a4-page`: 210mm de largura, padding = margens ABNT (25/20/30/20mm), Times New Roman 12pt, line-height 1.5, sombra.
- Tipografia jurídica: `h1,h2` centralizados 13pt; `p` justificado com `text-indent: 1.5cm`; classe `.clausula`; `.assinatura-bloco` flex com `.assinatura-linha` (border-top, 180pt).
- `.doc-var`: highlight azul para variáveis no editor (fundo #EEF4FF, borda #BFDBFE, fonte mono).
- Bloco `@page` para WeasyPrint com `@top-center`/`@bottom-center`.

**Critério de aceite:** mesmo CSS produz visual idêntico no editor e no PDF.

---

## FASE 7 — Editor TipTap (vendorizado)

### 7.1 Vendorizar o TipTap
Como produção é stack Portainer **sem pipeline NPM**, gerar o bundle uma única vez em dev e commitar:

1. Em uma pasta temporária (fora do repo): `npm init -y && npm i @tiptap/core @tiptap/starter-kit @tiptap/extension-text-align @tiptap/extension-table @tiptap/extension-table-row @tiptap/extension-table-cell @tiptap/extension-table-header @tiptap/extension-underline esbuild`
2. Criar `entry.js` exportando tudo em `window.TipTapBundle`:
```js
import { Editor, Node, mergeAttributes } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
window.TipTapBundle = { Editor, Node, mergeAttributes, StarterKit, TextAlign, Underline, Table, TableRow, TableCell, TableHeader }
```
3. `npx esbuild entry.js --bundle --minify --outfile=tiptap.bundle.min.js`
4. Copiar para `static/documentos/js/vendor/tiptap.bundle.min.js` e **commitar**. Servido via `collectstatic` — zero dependência externa em produção.

### 7.2 Extensão VariavelNode (nó atômico)
`static/documentos/js/variavel-node.js`:
```js
const { Node, mergeAttributes } = window.TipTapBundle;

const VariavelNode = Node.create({
	name: 'variavel',
	group: 'inline',
	inline: true,
	atom: true,                      // NÃO editável internamente
	addAttributes() {
		return { slug: { default: '' } };
	},
	parseHTML() {
		return [{ tag: 'span[data-var]' , getAttrs: el => ({ slug: el.getAttribute('data-var') }) }];
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
O HTML salvo no banco contém `<span data-var="cliente.nome" class="doc-var">{{ cliente.nome }}</span>` — a regex de validação e o render do Django funcionam direto sobre o texto `{{ cliente.nome }}`.

### 7.3 Tela do editor
`templates/documentos/modelo_editor.html`:
- Topbar: título (input), tipo (select), botões Preview A4 / Versões / Salvar.
- Toolbar: negrito, itálico, sublinhado, H1/H2/parágrafo, alinhar esq/centro/justificado, tabela, lista.
- Área central: div `.editor-a4-page` onde o TipTap monta.
- Sidebar direita: variáveis agrupadas por categoria (dados vindos de `{{ variaveis_json }}`), busca por texto, clique insere `VariavelNode` no cursor:
```js
editor.chain().focus().insertContent({ type: 'variavel', attrs: { slug } }).run();
```
- Salvar via fetch POST JSON → view valida com `validar_conteudo_modelo()` e retorna erros se houver.
- Autosave a cada 30s quando houver mudança (draft local em variável JS, sem localStorage).

**Critério de aceite:** criar modelo, inserir variáveis clicando, variáveis aparecem destacadas e não são editáveis por dentro, salvar valida allowlist, preview A4 renderiza com dados de exemplo (campo `exemplo` de `VariavelDocumento`).

---

## FASE 8 — Views, URLs e telas

Views finas chamando services. CBVs ou FBVs conforme padrão do GLOT.

### URLs (`apps/documentos/urls.py`, namespace `documentos`)
```text
/documentos/modelos/                       → lista de modelos
/documentos/modelos/novo/                  → editor (criar)
/documentos/modelos/<pk>/editar/           → editor (editar)
/documentos/modelos/<pk>/duplicar/         → POST duplicar
/documentos/modelos/<pk>/preview/          → preview com dados de exemplo
/documentos/modelos/<pk>/historico/        → versões do modelo
/documentos/gerar/venda/<venda_pk>/        → seleção de tipo+modelo e geração
/documentos/<pk>/                          → detalhe/preview do documento gerado
/documentos/<pk>/finalizar/                → POST finaliza (dispara PDF)
/documentos/<pk>/status/                   → JSON polling do PDF
/documentos/<pk>/substituir/               → POST gera novo a partir do mesmo modelo, marca anterior SUBSTITUIDO
/documentos/<pk>/cancelar/                 → POST cancela
/documentos/<pk>/pdf/                      → download do PDF (FileResponse com permissão)
/documentos/distratos/novo/venda/<venda_pk>/ → form do distrato
/documentos/distratos/<pk>/                → detalhe do distrato
/documentos/distratos/<pk>/concluir/       → POST concluir (atômico)
/documentos/variaveis/                     → lista de variáveis (referência p/ admin)
/empreendimentos/<pk>/documentos/          → tela de vínculo (EmpreendimentoDocumento) + ConfiguracaoDocumento
```

### Telas (Bootstrap/AdminLTE, padrão do GLOT)
1. **Lista de modelos**: título, tipo, global/específico, ativo, atualizado em; ações visualizar/editar/duplicar/inativar.
2. **Editor** (Fase 7).
3. **Configuração por empreendimento**: checkboxes de modelos agrupados por tipo + toggle "padrão" (um por tipo, validar via clean) + form da `ConfiguracaoDocumento` (logo, cabeçalho, rodapé, margens, fonte). Alerta se contrato/distrato sem padrão.
4. **Aba Documentos na venda**: tabela numero/título/status/gerado por/data/ações. Botão "Gerar documento" (modal: tipo → modelo padrão pré-selecionado, pode trocar). Ações por status: RASCUNHO = visualizar/finalizar/cancelar; FINALIZADO = download/substituir; SUBSTITUIDO/CANCELADO = só visualizar. **Nunca deletar.**
5. **Form do distrato**: motivo, data, valor devolução, % retenção, observação. Após salvar: botão "Gerar documento de distrato" → ao finalizar o PDF, habilita "Concluir distrato" (mostra aviso: venda será DISTRATADA e lote voltará a DISPONÍVEL).

### Integração no menu
Adicionar "Documentos" no menu lateral do GLOT com submenu: Modelos, Variáveis. (Distratos ficam acessíveis pela venda.)

**Critério de aceite:** fluxo completo manual: criar modelo → vincular ao empreendimento como padrão → abrir venda → gerar contrato → preview → finalizar → PDF baixável → substituir gera CTR novo e marca anterior. Distrato: criar → gerar doc → finalizar → concluir → venda DISTRATADA + lote DISPONIVEL.

---

## FASE 9 — Permissões

Sem fluxo de aprovação (decisão #6), mas com controle de acesso:

```python
GRUPOS = {
	'doc_admin':   ['add/change/view modelodocumento', 'change configuracaodocumento', 'change empreendimentodocumento', 'view variaveldocumento'],
	'doc_gerador': ['add/view documentogerado', 'finalizar/cancelar/substituir documento (custom)', 'add/change/view distrato', 'concluir distrato (custom)'],
	'doc_viewer':  ['view documentogerado', 'view modelodocumento'],
}
```
- Permissões custom em `Meta.permissions` dos models: `finalizar_documentogerado`, `cancelar_documentogerado`, `concluir_distrato`.
- Data migration criando os grupos.
- Decorators/mixins nas views.

**Critério de aceite:** usuário sem grupo não acessa nenhuma view do módulo; doc_viewer não consegue gerar.

---

## FASE 10 — Modelos iniciais (seed)

Data migration ou comando `python manage.py seed_modelos_documentos` criando 3 modelos globais (`eh_global=True`) a partir dos templates do backup da Fase 0 (adaptar variáveis para o novo padrão):

1. **Contrato de Compra e Venda** (tipo contrato) — partes (comprador com cônjuge condicional via `{% if %}`... *não*: sem tags `{% %}`; usar texto que funcione com cônjuge vazio), objeto (lote/quadra/empreendimento), valor + extenso, condições de pagamento, cláusulas padrão, bloco de assinaturas com local/data (`sistema.cidade_estado`, `sistema.data_hoje_extenso`).
2. **Proposta de Compra e Venda** (tipo proposta) — baseado no template legado existente no GLOT.
3. **Termo de Distrato** (tipo distrato) — referência ao contrato original, motivo, valor de devolução + extenso, % retenção, assinaturas.

**Critério de aceite:** os 3 modelos aparecem na lista, são pré-visualizáveis com dados de exemplo e geram PDF correto.

---

## FASE 11 — Testes

Suite pytest-django em `apps/documentos/tests/`:

- `test_services.py`: renderização segura (variável válida, inválida, tag `{% %}` bloqueada), contextos completos (com e sem cônjuge), numeração (sequência, virada de ano, prefixos), validação de modelo.
- `test_models.py`: imutabilidade do FINALIZADO, hash, incremento de versão + histórico, clean do padrão único por tipo, manager `para_empreendimento`/`padrao_para` (específico sobrepõe global).
- `test_distrato.py`: conclusão atômica (mock de falha → rollback total), exigência de documento finalizado, lote → disponível, venda → distratada.
- `test_views.py`: permissões por grupo, fluxo gerar→finalizar (Celery em modo eager: `CELERY_TASK_ALWAYS_EAGER=True` nos settings de teste), substituição, polling de status.
- `test_pdf.py`: task gera PDF válido (asserta magic bytes `%PDF`), retry em falha.

**Critério de aceite:** todos os testes verdes no CI (GitHub Actions já existente do GLOT).

---

## FASE 12 — Deploy

1. Atualizar `Dockerfile` (deps do WeasyPrint, requirements).
2. Atualizar a stack do Portainer: serviços `redis` e `celery-worker` (stack ID 48, endpoint 1 — usar o fluxo de redeploy via API já existente no CI/CD).
3. `collectstatic` inclui o bundle do TipTap.
4. Migrations em produção: executar manualmente via terminal do Portainer (fluxo atual do GLOT): `python manage.py migrate documentos`.
5. Smoke test em produção: criar 1 modelo, gerar 1 documento de teste, finalizar, baixar PDF, deletar o documento de teste via admin (única exceção à regra de não deletar — documento de teste).

---

## Observações finais para o Claude Code

- **Antes de codar a Fase 2**: ler os models reais de `vendas`, `clientes`, `lotes/quadras`, `empreendimentos` para acertar nomes de FKs, related_names e campos de status. NÃO assumir os nomes deste documento.
- **Campos do cliente**: o GLOT passou por consolidação recente do módulo clientes (campos `end_*` e `conj_*` no model único `Cliente`, telefones em `ClienteTelefone`). Os contextos da Fase 4 devem usar esses campos prefixados.
- O conteúdo dos templates legados de documentos (backup da Fase 0) é a fonte do texto jurídico dos modelos seed — não inventar cláusulas novas.
- Commits pequenos por fase, no padrão trunk-based do projeto.
- Em caso de dúvida sobre nome de campo/model: inspecionar o código, nunca inventar.
