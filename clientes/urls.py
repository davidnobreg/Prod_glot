from django.urls import path  # adicionar include
from . import views

urlpatterns = [
    # Cadastro de cliente
    path('insert_cliente/', views.criarCliente, name='criar-cliente'),

    path('select/<int:cliente_id>/', views.selectCliente, name='select-cliente'),
    path('insert_cliente_modal/', views.criarClienteModal, name='criar-cliente-modal'),
    path('update/<int:cliente_id>/', views.alteraCliente, name='altera-cliente'),
    path('delete_cliente/<int:id>/', views.deleteCliente, name='delete-cliente'),
    path('listar_clientes/', views.listaCliente, name='lista-cliente'),

    #path('listar_clientes_filtro/', views.reports, name='lista-cliente-filtro'),
]
