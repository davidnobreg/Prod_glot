from django.urls import path
from .views import criar_Venda, criar_Reservado, lista_Venda, lista_Reserva, reservado, delete_venda, delete_reseva, cancelar_Reservado

urlpatterns = [
    # Cadastro de cliente
    path('insert_venda/<int:id>/', criar_Venda, name='criar-venda'),
    path('insert_reserva/<int:id>/', criar_Reservado, name='reserva-create'),
    path('listar_reserva/', lista_Reserva, name='lista-reserva'),
    path('listar_venda/', lista_Venda, name='lista-venda'),
    path('reservado/<int:id>/', reservado, name='reservado'),
    path('reservado_cancelada/<int:id>/', cancelar_Reservado, name='cancelar-reservado'),
    path('venda_delete/<int:id>/', delete_venda, name='delete-venda'),
    path('reservado_delete/<int:id>/', delete_reseva, name='delete-reservado'),
]
