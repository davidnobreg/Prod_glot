from django.urls import path
from . import views


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
    path('venda_delete/<int:id>/', views.deleteVenda, name='delete-venda'),
    path('reservado_delete/<int:id>/', views.deleteReseva, name='delete-reservado'),
    path('renova_reserva/<int:id>/', views.renovaReserva, name='renova-reserva'),
]
