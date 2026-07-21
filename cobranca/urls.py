from django.urls import path

from .views import (
	BaixaManualParcelaView,
	DetalheCarneView,
	DetalheParcelaView,
	GerarCarneView,
	GerarEntradaView,
	ListaCarnesVendaView,
)

urlpatterns = [
	path('venda/<uuid:venda_uuid>/carnes/', ListaCarnesVendaView.as_view(), name='lista_carnes_venda'),
	path('venda/<uuid:venda_uuid>/gerar-carne/', GerarCarneView.as_view(), name='gerar_carne'),
	path('venda/<uuid:venda_uuid>/gerar-entrada/', GerarEntradaView.as_view(), name='gerar_entrada'),
	path('carne/<uuid:carne_uuid>/', DetalheCarneView.as_view(), name='detalhe_carne'),
	path('parcela/<uuid:parcela_uuid>/baixa-manual/', BaixaManualParcelaView.as_view(), name='baixa_manual_parcela'),
	path('parcela/<uuid:parcela_uuid>/', DetalheParcelaView.as_view(), name='detalhe_parcela'),
]
