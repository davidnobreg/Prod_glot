from django.urls import path
from .views.create_views import (
    CriarReservadoView
)

urlpatterns = [
    # Cadastro de cliente
    path('insert_venda/<uuid:venda_uuid>/', views.criarVenda, name='criar-venda'),



    path('reservado_cancelada/<int:id>/', views.cancelarReservado, name='cancelar-reservado'),








]
