import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from datetime import datetime
from clientes.models import Cliente
from empreendimentos.models import Lote, Empreendimento
from accounts.models import User

EXTENSOES_DOCUMENTO_ASSINADO = ('pdf', 'jpg', 'jpeg', 'png')


def validate_documento_assinado(value):
	ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
	if ext not in EXTENSOES_DOCUMENTO_ASSINADO:
		raise ValidationError('Envie PDF, JPG ou PNG.')
	if value.size > 10 * 1024 * 1024:
		raise ValidationError('Arquivo não pode exceder 10 MB.')


class TypeVenda(models.TextChoices):
	CANCELADA = 'CANCELADA', 'CANCELADA'
	RESERVADO = 'RESERVADO', 'RESERVADO'
	VENDIDO = 'VENDIDO', 'VENDIDO'
	ANALISE = 'ANALISE', 'ANALISE'
	NAO_ACEITE = 'NAO_ACEITE', 'NAO-ACEITE'
	PRE_VENDA = 'PRE-VENDA', 'PRE-VENDA'

## Registrar Venda

class RegisterVenda(models.Model):

	id = models.BigAutoField(primary_key=True)
	uuid = models.UUIDField(
	    default=uuid.uuid4,
	    editable=False,
	    unique=True,
	    db_index=True
	)
	lote = models.OneToOneField(Lote, on_delete=models.SET_NULL, blank=True, null=True, related_name='reg_venda')
	cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, blank=True, null=True)
	corretor = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="corretor")
	tipo_venda = models.CharField(max_length=100, choices=TypeVenda.choices)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="vendas")
	aceite_proposta = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="aceite_proposta")
	dt_reserva = models.DateField(default=datetime.now, blank=True)
	dt_venda = models.DateField(blank=True, null=True)
	create_at = models.DateField(default=datetime.now, blank=True)
	is_ativo = models.BooleanField(default=False)
	quantidade_parcelas = models.IntegerField(blank=True, null=True,)
	quantidade_parcelas_pagas = models.IntegerField(blank=True, null=True,)
	valor_inicio_contrato = models.DecimalField('Valor do Contrato', max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
	valor_financiado = models.DecimalField('Valor do Financiamento', max_digits=50, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
	valor_sinal = models.DecimalField('Valor do Sinal', max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
	valor_entrada = models.DecimalField('Valor do Entrada', max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
	dt_primeira_parcela = models.DateField('Data para primeira parcela', blank=True, null=True)
	reajuste = models.BooleanField(default=True)
	valor_parcela = models.DecimalField('Valor da Parcela', max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
	valor_desconto = models.DecimalField(
	    max_digits=12,
	    decimal_places=2,
	    default=0,
	    verbose_name='Desconto'
	)
	observacao = models.TextField(blank=True)
	corretor_nome = models.CharField(max_length=255, blank=True, default='')


	def __str__(self):
	    if self.lote:
	        return "{} - lote {} quadra {} - {} - status {} - valor-sinal {}".format(
	            self.cliente,
	            self.lote,
	            self.lote.quadra.namequadra,
	            self.lote.quadra.empr,
	            self.tipo_venda,
	            self.valor_sinal,
	        )
	    return "{} - sem lote - status {}".format(self.cliente, self.tipo_venda)

	class Meta:
	    verbose_name = 'Registrar Venda'
	    verbose_name_plural = 'Registrar Venda'
	    ordering = ['-id']


class RegisterVendaIntercalada(models.Model):

	venda = models.ForeignKey(RegisterVenda, on_delete=models.CASCADE, blank=True, null=True, related_name='intercaladas')
	quantidade_parcelas_intercalada = models.IntegerField('quantidade de intercaladas', blank=True, null=True)
	valor_intercalada = models.CharField('Valor da intercalada', blank=True, null=True, max_length=50, default=00.00)


class VendaDocumentoQuerySet(models.QuerySet):
	def vigentes(self):
		return self.exclude(status='arquivado')


class VendaDocumento(models.Model):

	TIPO_CHOICES = [
		('proposta_assinada', 'Proposta Assinada'),
		('contrato_assinado', 'Contrato Assinado'),
		('outros', 'Outros'),
	]
	STATUS_CHOICES = [
		('pendente', 'Pendente'),
		('enviado', 'Enviado'),
		('aprovado', 'Aprovado'),
		('rejeitado', 'Rejeitado'),
		('arquivado', 'Arquivado'),
	]

	objects = VendaDocumentoQuerySet.as_manager()

	uuid = models.UUIDField(
	    default=uuid.uuid4,
	    editable=False,
	    unique=True,
	    db_index=True
	)
	venda = models.ForeignKey(RegisterVenda, on_delete=models.CASCADE, related_name='documentos_assinados')
	tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='outros')
	arquivo_assinado = models.FileField(
		upload_to='vendas/documentos_assinados/',
		validators=[validate_documento_assinado],
	)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enviado')
	ciclo = models.PositiveIntegerField(default=1)
	observacao = models.TextField(blank=True)
	enviado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='documentos_enviados')
	enviado_em = models.DateTimeField(auto_now_add=True)
	aprovado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_aprovados')
	aprovado_em = models.DateTimeField(null=True, blank=True)
	documento_gerado = models.ForeignKey(
		'documentos.DocumentoGerado',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)

	class Meta:
		ordering = ['-enviado_em']
		verbose_name = 'Documento de Venda'
		verbose_name_plural = 'Documentos de Venda'
		constraints = [
			models.UniqueConstraint(
				fields=['venda', 'tipo'],
				condition=Q(status='aprovado'),
				name='unico_aprovado_por_venda_tipo',
			),
		]

	def __str__(self):
		return f"{self.get_tipo_display()} — {self.venda}"


# Mapeamento de tipos de VendaDocumento (upload assinado) para TipoDocumento (DocumentoGerado)
TIPO_ASSINADO_PARA_GERADO = {
	'proposta_assinada': 'proposta',
	'contrato_assinado': 'contrato',
}