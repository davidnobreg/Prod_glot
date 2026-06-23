import uuid
from decimal import Decimal
from django.db import models
from datetime import datetime
from clientes.models import Cliente
from empreendimentos.models import Lote, Empreendimento
from accounts.models import User


class TypeVenda(models.TextChoices):
	CANCELADA = 'CANCELADA', 'CANCELADA'
	RESERVADO = 'RESERVADO', 'RESERVADO'
	VENDIDO = 'VENDIDO', 'VENDIDO'
	ANALISE = 'ANALISE', 'ANALISE'
	NAO_ACEITE = 'NAO-ACEITE', 'NAO-ACEITE'
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
	    return "{} - lote {} quadra- {} - {} - status {} - valor-sinal {}".format(self.cliente, self.lote, self.lote.quadra.namequadra,
	                                                 self.lote.quadra.empr, self.tipo_venda, self.valor_sinal)

	class Meta:
	    verbose_name = 'Registrar Venda'
	    verbose_name_plural = 'Registrar Venda'
	    ordering = ['-id']


class RegisterVendaIntercalada(models.Model):

	venda = models.ForeignKey(RegisterVenda, on_delete=models.CASCADE, blank=True, null=True, related_name='intercaladas')
	quantidade_parcelas_intercalada = models.IntegerField('quantidade de intercaladas', blank=True, null=True)
	valor_intercalada = models.CharField('Valor da intercalada', blank=True, null=True, max_length=50, default=00.00)