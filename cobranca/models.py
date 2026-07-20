import uuid

from django.conf import settings
from django.db import models

from .fields import EncryptedCharField, EncryptedTextField


class ConfiguracaoGateway(models.Model):

	GATEWAY_CHOICES = [
		('banco_brasil', 'Banco do Brasil'),
		('sicredi', 'Sicredi'),
		('sicoob', 'Sicoob'),
		('bradesco', 'Bradesco'),
		('banco_nordeste', 'Banco do Nordeste'),
		('caixa_economica', 'Caixa Econômica Federal'),
	]

	id = models.BigAutoField(primary_key=True)
	uuid = models.UUIDField(
		default=uuid.uuid4,
		editable=False,
		unique=True,
		db_index=True,
	)
	empreendimento = models.OneToOneField(
		'empreendimentos.Empreendimento',
		on_delete=models.CASCADE,
		related_name='configuracao_gateway',
	)
	gateway = models.CharField(max_length=30, choices=GATEWAY_CHOICES, null=True, blank=True)
	client_id = EncryptedCharField(max_length=255, null=True, blank=True)
	client_secret = EncryptedCharField(max_length=255, null=True, blank=True)
	convenio = EncryptedCharField(max_length=100, null=True, blank=True)
	certificado = EncryptedTextField(null=True, blank=True)
	chave_certificado = EncryptedTextField(null=True, blank=True)
	sandbox = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Configuração de Gateway'
		verbose_name_plural = 'Configurações de Gateway'

	def __str__(self):
		return f'{self.empreendimento} — {self.gateway or "sem gateway"}'


class Carne(models.Model):

	STATUS_CHOICES = [
		('GERADO', 'Gerado'),
		('ENVIADO', 'Enviado ao Banco'),
		('CANCELADO', 'Cancelado'),
	]

	id = models.BigAutoField(primary_key=True)
	uuid = models.UUIDField(
		default=uuid.uuid4,
		editable=False,
		unique=True,
		db_index=True,
	)
	venda = models.ForeignKey(
		'vendas.RegisterVenda',
		on_delete=models.PROTECT,
		related_name='carnes',
	)
	numero_carne = models.PositiveIntegerField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='GERADO')
	ano_referencia = models.PositiveIntegerField()
	gerado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name='carnes_gerados',
	)
	observacoes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('venda', 'numero_carne')]
		verbose_name = 'Carnê'
		verbose_name_plural = 'Carnês'
		ordering = ['-ano_referencia', 'numero_carne']

	def __str__(self):
		return f'Carnê {self.numero_carne}/{self.ano_referencia} — venda {self.venda_id}'


class Parcela(models.Model):

	TIPO_CHOICES = [
		('ENTRADA', 'Entrada'),
		('PARCELA', 'Parcela'),
	]
	MODALIDADE_CHOICES = [
		('BOLETO', 'Boleto Bancário'),
		('MANUAL', 'Baixa Manual'),
	]
	STATUS_CHOICES = [
		('PENDENTE', 'Pendente'),
		('ENVIADA_BANCO', 'Enviada ao Banco'),
		('PAGA', 'Paga'),
		('CANCELADA', 'Cancelada'),
		('INADIMPLENTE', 'Inadimplente'),
	]

	id = models.BigAutoField(primary_key=True)
	uuid = models.UUIDField(
		default=uuid.uuid4,
		editable=False,
		unique=True,
		db_index=True,
	)
	carne = models.ForeignKey(
		'cobranca.Carne',
		on_delete=models.PROTECT,
		related_name='parcelas',
		null=True,
		blank=True,
	)
	venda = models.ForeignKey(
		'vendas.RegisterVenda',
		on_delete=models.PROTECT,
		related_name='parcelas',
	)
	tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='PARCELA')
	modalidade = models.CharField(max_length=10, choices=MODALIDADE_CHOICES, default='BOLETO')
	numero_parcela = models.PositiveIntegerField()
	valor = models.DecimalField(max_digits=12, decimal_places=2)
	valor_pago = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	data_vencimento = models.DateField()
	data_pagamento = models.DateField(null=True, blank=True)
	igpm_aplicado = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
	baixado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.PROTECT,
		related_name='parcelas_baixadas',
	)
	observacoes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('carne', 'numero_parcela')]
		verbose_name = 'Parcela'
		verbose_name_plural = 'Parcelas'
		ordering = ['venda', 'numero_parcela']

	def __str__(self):
		return f'Parcela {self.numero_parcela} — venda {self.venda_id}'


class CobrancaBancaria(models.Model):

	STATUS_CHOICES = [
		('PENDENTE', 'Pendente'),
		('REGISTRADA', 'Registrada no Banco'),
		('PAGA', 'Paga'),
		('CANCELADA', 'Cancelada'),
		('ERRO', 'Erro'),
	]

	id = models.BigAutoField(primary_key=True)
	uuid = models.UUIDField(
		default=uuid.uuid4,
		editable=False,
		unique=True,
		db_index=True,
	)
	parcela = models.ForeignKey(
		'cobranca.Parcela',
		on_delete=models.PROTECT,
		related_name='cobrancas_bancarias',
	)
	ativa = models.BooleanField(default=True)
	gateway = models.CharField(max_length=30)
	nosso_numero = models.CharField(max_length=50, null=True, blank=True)
	linha_digitavel = models.TextField(null=True, blank=True)
	codigo_barras = models.TextField(null=True, blank=True)
	url_boleto = models.URLField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
	resposta_banco = models.JSONField(null=True, blank=True)
	erro_mensagem = models.TextField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Cobrança Bancária'
		verbose_name_plural = 'Cobranças Bancárias'
		ordering = ['-created_at']

	def __str__(self):
		return f'Cobrança {self.nosso_numero or self.uuid} — {self.status}'
