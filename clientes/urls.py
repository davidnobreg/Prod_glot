from django.urls import path  # adicionar include
from . import views

urlpatterns = [
    # Cadastro de cliente
    path('insert_cliente/', views.criarCliente, name='criar-cliente'),
    path('select/<uuid:cliente_uuid>/', views.selectCliente, name='select-cliente'),
    path('select_endereco/<int:endereco_id>/', views.selectClienteEndereco, name='select-cliente-endereco'),
    path('update/<uuid:cliente_uuid>/', views.atualizarCliente, name='atualizar-cliente'),
    path('delete_cliente/<uuid:cliente_uuid>/', views.deleteCliente, name='delete-cliente'),
    path('listar_clientes/', views.listaCliente, name='lista-cliente'),
    path('listar_clientes_relatorio/', views.listaClienteRelatorio, name='lista-cliente-relatorio'),

    # path('listar_clientes_filtro/', views.reports, name='lista-cliente-filtro'),
]
