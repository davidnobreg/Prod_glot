from django.urls import path  # adicionar include
from . import views

urlpatterns = [
    # Cadastro de cliente
    path('insert_cliente/', views.criarCliente, name='criar-cliente'),
    path('select/<uuid:cliente_uuid>/', views.selectCliente, name='select-cliente'),
    path('update/<uuid:cliente_uuid>/', views.atualizarCliente, name='atualizar-cliente'),
    path('delete_cliente/<uuid:cliente_uuid>/', views.deleteCliente, name='delete-cliente'),
    path('listar_clientes/', views.listaCliente, name='lista-cliente'),
    path('listar_clientes_relatorio/', views.listaClienteRelatorio, name='lista-cliente-relatorio'),
    path('<uuid:cliente_uuid>/documentos/adicionar/', views.adicionar_documento_cliente, name='adicionar-documento-cliente'),
    path('documentos/<uuid:documento_uuid>/excluir/', views.excluir_documento_cliente, name='excluir-documento-cliente'),
    path('<uuid:cliente_uuid>/wizard/arquivo-add/', views.wizard_arquivo_add, name='wizard-arquivo-add'),
    path('<uuid:cliente_uuid>/wizard/arquivo-del/<uuid:documento_uuid>/', views.wizard_arquivo_del, name='wizard-arquivo-del'),
    path('<uuid:cliente_uuid>/wizard/representante/add/', views.wizard_representante_add, name='wizard-representante-add'),
    path('<uuid:cliente_uuid>/wizard/representante/<uuid:representante_uuid>/del/', views.wizard_representante_del, name='wizard-representante-del'),
    path('wizard/representante/<uuid:representante_uuid>/arquivo-add/', views.wizard_representante_arquivo_add, name='wizard-representante-arquivo-add'),
    path('wizard/representante/arquivo-del/<uuid:documento_uuid>/', views.wizard_representante_arquivo_del, name='wizard-representante-arquivo-del'),
    path('wizard/salvar-passo/', views.wizard_salvar_passo, name='wizard-salvar-passo'),
    path('<uuid:cliente_uuid>/wizard/finalizar/', views.wizard_finalizar, name='wizard-finalizar'),

    # path('listar_clientes_filtro/', views.reports, name='lista-cliente-filtro'),
]
