from django.urls import path
from . import views
from django.conf import settings

urlpatterns = [
    # Cadastro de cliente
    path('insert_venda/<uuid:venda_uuid>/', views.criarVenda, name='criar-venda'),
    path('insert_reserva/<uuid:reserva_uuid>/', views.criarReservado, name='reserva-create'),
    path('listar_reserva/', views.listaReserva, name='lista-reserva'),
    path('listar_venda/', views.listaVenda, name='lista-venda'),
    path('listar_venda_relatorio/', views.listaVendaRelatorio, name='lista-venda-relatorio'),
    path('reservado/<uuid:lote_uuid>/', views.reservado, name='reservado'),
    path('reservado_detalhes/<uuid:reserva_uuid>/', views.reservadoDetalhe, name='reservadoDetalhes'),
    path('reservado_cancelada/<int:id>/', views.cancelarReservado, name='cancelar-reservado'),
    path('reservado_cancelada_cadastro/<uuid:cancelaReserva_uuid>/', views.cancelarReservadoCadastro, name='cancelar-reservado-cadastro'),
    path('reserva_temporario/<uuid:lote_uuid>/', views.reserva_temporaria, name='reserva_temporaria'),
    path('venda_delete/<uuid:delete_uuid>/', views.deleteVenda, name='delete-venda'),
    path('reservado_delete/<int:id>/', views.deleteReseva, name='delete-reservado'),
    path('reservado_delete_lista/<int:id>/', views.deleteResevaLista, name='delete-reservado-lista'),
    path('renova_reserva/<uuid:venda_uuid>/', views.renovaReserva, name='renova-reserva'),
    path('select/<int:venda_id>/', views.renovaReserva, name='renova-reserva'),



]
