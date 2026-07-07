import hashlib
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


# Create your models here.
class CadastroDocumento(models.Model):
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título do Contrato"
    )

    texto = models.TextField(
        verbose_name="Texto do Contrato"
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ('proposta', 'Proposta'),
            ('contrato', 'Contrato'),
            ('distrato', 'Distrato'),
            ('distrato_inadimp', 'Distrato por Inadimplência'),
            ('cessao', 'Cessão'),
            ('aluguel', 'Contrato de Aluguel'),
            ('outros', 'Outros Papeis'),
            ('reserva', 'Contrato de Reserva'),
            ('venda', 'Contrato de Venda'),
        ]
    )
    versao = models.IntegerField(default=1)

    ativo = models.BooleanField(default=True)

    variaveis_disponiveis = models.TextField(
        blank=True,
        verbose_name="Variáveis disponíveis"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titulo


# ==========================================================
# MÓDULO DE DOCUMENTOS — reestruturação (PLANO_MODULO_DOCUMENTOS)
# Novos models convivem com CadastroDocumento (migração in-place)
# ==========================================================

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


class StatusDocumento(models.TextChoices):
	RASCUNHO = 'rascunho', 'Rascunho'
	PROCESSANDO = 'processando', 'Processando'
	FINALIZADO = 'finalizado', 'Finalizado'
	CANCELADO = 'cancelado', 'Cancelado'
	SUBSTITUIDO = 'substituido', 'Substituído'
	ERRO = 'erro', 'Erro'


# ----------------------------------------------------------
# Variáveis globais
# ----------------------------------------------------------
class VariavelDocumento(models.Model):
	CATEGORIAS = [
		('cliente', 'Cliente'), ('conjuge', 'Cônjuge'),
		('empreendimento', 'Empreendimento'), ('lote', 'Lote / Quadra'),
		('venda', 'Venda'), ('distrato', 'Distrato'), ('sistema', 'Sistema'),
	]
	categoria = models.CharField(max_length=30, choices=CATEGORIAS)
	tag_slug = models.CharField(max_length=100, unique=True)
	label = models.CharField(max_length=100)
	exemplo = models.CharField(max_length=200, blank=True)
	ativo = models.BooleanField(default=True)
	ordem = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['categoria', 'ordem', 'label']
		verbose_name = 'Variável de documento'
		verbose_name_plural = 'Variáveis de documento'

	@property
	def tag(self):
		return '{{ %s }}' % self.tag_slug

	def __str__(self):
		return self.tag_slug


# ----------------------------------------------------------
# Modelo de documento (template reutilizável)
# ----------------------------------------------------------
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


class ModeloDocumento(models.Model):
	uuid = models.UUIDField(
		default=uuid.uuid4,
		editable=False,
		unique=True,
		db_index=True
	)
	titulo = models.CharField(max_length=255)
	tipo = models.CharField(max_length=30, choices=TipoDocumento.choices)
	conteudo_html = models.TextField(blank=True)
	eh_global = models.BooleanField(default=False)
	versao = models.PositiveIntegerField(default=1)
	ativo = models.BooleanField(default=True)
	criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	objects = ModeloDocumentoManager()

	class Meta:
		ordering = ['tipo', 'titulo']
		verbose_name = 'Modelo de documento'
		verbose_name_plural = 'Modelos de documento'

	def __str__(self):
		return f'{self.titulo} (v{self.versao})'

	def save(self, *args, **kwargs):
		# Em update com mudança de conteúdo: incrementa versão e
		# arquiva o conteúdo ANTERIOR em ModeloDocumentoHistorico.
		if self.pk:
			anterior = ModeloDocumento.objects.filter(pk=self.pk).first()
			if anterior and anterior.conteudo_html != self.conteudo_html:
				editor = getattr(self, '_editado_por', None) or self.criado_por
				self.versao = anterior.versao + 1
				super().save(*args, **kwargs)
				ModeloDocumentoHistorico.objects.create(
					modelo=self,
					versao=anterior.versao,
					conteudo_html=anterior.conteudo_html,
					editado_por=editor,
				)
				return
		super().save(*args, **kwargs)


class ModeloDocumentoHistorico(models.Model):
	modelo = models.ForeignKey(ModeloDocumento, on_delete=models.CASCADE, related_name='historico')
	versao = models.PositiveIntegerField()
	conteudo_html = models.TextField()
	editado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	editado_em = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-versao']
		verbose_name = 'Histórico de modelo'
		verbose_name_plural = 'Históricos de modelo'

	def __str__(self):
		return f'{self.modelo_id} v{self.versao}'


# ----------------------------------------------------------
# Vínculo empreendimento ↔ modelo
# ----------------------------------------------------------
class EmpreendimentoDocumento(models.Model):
	empreendimento = models.ForeignKey('empreendimentos.Empreendimento', on_delete=models.CASCADE, related_name='documentos_config')
	modelo = models.ForeignKey(ModeloDocumento, on_delete=models.PROTECT, related_name='empreendimentos_vinculo')
	padrao = models.BooleanField(default=False)
	ativo = models.BooleanField(default=True)
	ordem = models.PositiveSmallIntegerField(default=0)

	class Meta:
		unique_together = ('empreendimento', 'modelo')
		ordering = ['modelo__tipo', 'ordem']
		verbose_name = 'Vínculo empreendimento/modelo'
		verbose_name_plural = 'Vínculos empreendimento/modelo'

	def __str__(self):
		return f'{self.empreendimento_id} → {self.modelo_id}'

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


# ----------------------------------------------------------
# Configuração de documento por empreendimento (cabeçalho/rodapé)
# ----------------------------------------------------------
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

	class Meta:
		verbose_name = 'Configuração de documento'
		verbose_name_plural = 'Configurações de documento'

	def __str__(self):
		return f'Config {self.empreendimento_id}'


# ----------------------------------------------------------
# Numeração sequencial por tipo + ano
# ----------------------------------------------------------
class SequencialDocumento(models.Model):
	tipo = models.CharField(max_length=30)
	ano = models.PositiveSmallIntegerField()
	ultimo = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = ('tipo', 'ano')
		verbose_name = 'Sequencial de documento'
		verbose_name_plural = 'Sequenciais de documento'

	def __str__(self):
		return f'{self.tipo}-{self.ano}: {self.ultimo}'

	@classmethod
	def proximo_numero(cls, tipo):
		"""Gera CTR-2025-0042. Chamar SEMPRE dentro de transaction.atomic()."""
		ano = timezone.now().year
		seq, _ = cls.objects.select_for_update().get_or_create(tipo=tipo, ano=ano)
		seq.ultimo += 1
		seq.save(update_fields=['ultimo'])
		prefixo = PREFIXO_POR_TIPO.get(tipo, 'DOC')
		return f'{prefixo}-{ano}-{seq.ultimo:04d}'


# ----------------------------------------------------------
# Distrato
# ----------------------------------------------------------
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

	class Meta:
		ordering = ['-criado_em']
		verbose_name = 'Distrato'
		verbose_name_plural = 'Distratos'
		permissions = [
			('concluir_distrato', 'Pode concluir distrato'),
		]

	def __str__(self):
		return f'Distrato venda {self.venda_id}'


# ----------------------------------------------------------
# Documento gerado (instância final, imutável quando finalizada)
# ----------------------------------------------------------
class DocumentoGerado(models.Model):
	uuid = models.UUIDField(
		default=uuid.uuid4,
		editable=False,
		unique=True,
		db_index=True
	)
	numero = models.CharField(max_length=20, unique=True, editable=False)
	modelo = models.ForeignKey(ModeloDocumento, on_delete=models.PROTECT)
	modelo_versao_snapshot = models.PositiveIntegerField()
	venda = models.ForeignKey('vendas.RegisterVenda', on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
	cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
	distrato = models.ForeignKey('documentos.Distrato', on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
	titulo = models.CharField(max_length=255)
	conteudo_final_html = models.TextField()
	status = models.CharField(max_length=20, choices=StatusDocumento.choices, default=StatusDocumento.RASCUNHO)
	hash_conteudo = models.CharField(max_length=64, blank=True)
	arquivo_pdf = models.FileField(upload_to='documentos/pdf/%Y/%m/', null=True, blank=True)
	arquivo_word = models.FileField(upload_to='documentos/word/%Y/%m/', null=True, blank=True)
	substitui = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='substituido_por')
	criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
	criado_em = models.DateTimeField(auto_now_add=True)
	finalizado_em = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-criado_em']
		verbose_name = 'Documento gerado'
		verbose_name_plural = 'Documentos gerados'
		permissions = [
			('finalizar_documentogerado', 'Pode finalizar documento'),
			('cancelar_documentogerado', 'Pode cancelar documento'),
		]

	# Campos imutáveis quando status == FINALIZADO
	_IMUTAVEIS = ('conteudo_final_html', 'numero', 'modelo_id', 'venda_id')

	def __str__(self):
		return self.numero

	def save(self, *args, **kwargs):
		if self.pk:
			anterior = DocumentoGerado.objects.filter(pk=self.pk).first()
			if anterior and anterior.status == StatusDocumento.FINALIZADO:
				for campo in self._IMUTAVEIS:
					if getattr(anterior, campo) != getattr(self, campo):
						raise ValidationError(
							'Documento finalizado é imutável; gere um novo documento.'
						)
		else:
			if not self.numero:
				with transaction.atomic():
					self.numero = SequencialDocumento.proximo_numero(self.modelo.tipo)
		super().save(*args, **kwargs)
