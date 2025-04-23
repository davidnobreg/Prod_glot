from django.urls import path
from .views import criarEmpreendimento, listaEmpreendimento, listaEmpreendimentoTabela, listaQuadra, \
    deleteEmpreendimento, alteraEmpreendimento, selectEmpreendimento,detalheEmpreendimento, \
    importarDados

urlpatterns = [
    # Cadastro de cliente
    path('insert_empreendimento/', criarEmpreendimento, name='criar-empreendimento'),

    path('select/<int:empreendimento_id>/', selectEmpreendimento, name='select-empreendimento'),

    path('alterar_empreendimento/<int:id>/', alteraEmpreendimento, name='alterar-empreendimento'),

    path('deleta_empreendimento/<int:empreendimento_Id>/', deleteEmpreendimento, name='deletar-empreendimento'),

    path('insert_arq/<int:id>/', importarDados.as_view(), name='arquivo'),

    path('', listaEmpreendimento, name='lista-empreendimento'),

    path('listar_empreendimento/', listaEmpreendimentoTabela, name='lista-empreendimento-tabela'),

    path('listar_quadras/<int:id>/', listaQuadra, name='listar-quadras'),
    path('detalhe_empreendimento/<int:id>/', detalheEmpreendimento, name='detalhe-empreendimento')

]
