from django.urls import path
from . import views
from django.conf import settings

urlpatterns = [
    # Cadastro de cliente
    path('insert_venda/<int:id>/', views.criarVenda, name='criar-venda'),
    path('insert_reserva/<int:id>/', views.criarReservado, name='reserva-create'),
    path('listar_reserva/', views.listaReserva, name='lista-reserva'),
    path('listar_venda/', views.listaVenda, name='lista-venda'),
    path('listar_venda_relatorio/', views.listaVendaRelatorio, name='lista-venda-relatorio'),
    path('reservado/<int:id>/', views.reservado, name='reservado'),
    path('reservado_detalhes/<int:id>/', views.reservadoDetalhe, name='reservadoDetalhes'),
    path('reservado_cancelada/<int:id>/', views.cancelarReservado, name='cancelar-reservado'),
    path('reservado_cancelada_cadastro/<int:id>/', views.cancelarReservadoCadastro, name='cancelar-reservado-cadastro'),
    path('reserva_temporario/<int:lote_id>/', views.reserva_temporaria, name='reserva_temporaria'),
    path('venda_delete/<int:id>/', views.deleteVenda, name='delete-venda'),
    path('reservado_delete/<int:id>/', views.deleteReseva, name='delete-reservado'),
    path('reservado_delete_lista/<int:id>/', views.deleteResevaLista, name='delete-reservado-lista'),
    path('renova_reserva/<int:id>/', views.renovaReserva, name='renova-reserva'),
    path('select/<int:venda_id>/', views.renovaReserva, name='renova-reserva'),
    path('proposta/', views.proposta, name='proposta'),
    path('proposta/pdf/', views.proposta_pdf, name='proposta'),
    path('documento/<int:venda_id>/', views.visualizar_documento, name='visualizar_documento'),
    path('documento/pdf/', views.documento_pdf, name='documento_pdf'),


]
