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
    path('<uuid:cliente_uuid>/documentos/adicionar/', views.adicionar_documento_cliente, name='adicionar-documento-cliente'),
    path('documentos/<int:documento_id>/excluir/', views.excluir_documento_cliente, name='excluir-documento-cliente'),
    path('<uuid:cliente_uuid>/wizard/arquivo-add/', views.wizard_arquivo_add, name='wizard-arquivo-add'),
    path('wizard/arquivo-del/<int:documento_id>/', views.wizard_arquivo_del, name='wizard-arquivo-del'),
    path('wizard/salvar-passo/', views.wizard_salvar_passo, name='wizard-salvar-passo'),
    path('<uuid:cliente_uuid>/wizard/finalizar/', views.wizard_finalizar, name='wizard-finalizar'),

    # path('listar_clientes_filtro/', views.reports, name='lista-cliente-filtro'),
]
