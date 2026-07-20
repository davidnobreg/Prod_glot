from django.contrib import admin

from .models import Carne, CobrancaBancaria, ConfiguracaoGateway, Parcela


@admin.register(ConfiguracaoGateway)
class ConfiguracaoGatewayAdmin(admin.ModelAdmin):
	list_display = ['empreendimento', 'gateway', 'sandbox', 'created_at']
	# NÃO incluir campos criptografados em list_display


@admin.register(Carne)
class CarneAdmin(admin.ModelAdmin):
	list_display = ['uuid', 'venda', 'numero_carne', 'ano_referencia', 'status', 'created_at']
	raw_id_fields = ['venda']


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
	list_display = ['uuid', 'venda', 'tipo', 'numero_parcela', 'valor', 'data_vencimento', 'status']
	raw_id_fields = ['venda', 'carne']


@admin.register(CobrancaBancaria)
class CobrancaBancariaAdmin(admin.ModelAdmin):
	list_display = ['uuid', 'parcela', 'gateway', 'ativa', 'status', 'created_at']
