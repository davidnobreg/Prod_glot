from django.urls import path  # adicionar include
from . import views

urlpatterns = [
    # Cadastro de cliente
    path('insert_cliente/', views.criar_cliente, name='criar-cliente'),

    path('select/<int:cliente_id>/', views.select_cliente, name='select-cliente'),
    path('insert_cliente_modal/', views.criar_cliente_modal, name='criar-cliente-modal'),
    path('update/<int:cliente_id>/', views.altera_cliente, name='altera-cliente'),
    path('delete_cliente/<int:id>/', views.delete_cliente, name='delete-cliente'),
    path('listar_clientes/', views.lista_cliente, name='lista-cliente'),
]
