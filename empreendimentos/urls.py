from django.urls import path
from .views import (criarEmpreendimento, listaEmpreendimento, listaEmpreendimentoTabela, listaQuadra, \
                    deleteEmpreendimento, alteraEmpreendimento, selectEmpreendimento, detalheEmpreendimento,
                    relatorioFinanceiro, reservadoDetalheEmpreendimento, listaReservasTemporaria,
                    cancelarReservadoTemporaria, cancelarReservadoTemporariaLista, \
                    alteraLote, renovaReserva, liberaLote, gerarRelatorioLotes, \
                    importarDados)

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

    path('detalhe_empreendimento/<int:id>/', detalheEmpreendimento, name='detalhe-empreendimento'),

    path('relatorio_financeiro/<int:id>/', relatorioFinanceiro, name='relatorio-financeiro'),

    path('reserva_temporario/<int:id>/', alteraLote, name='alterar-lote'),

    path('reservado_detalhes_pre_reserva_lote/<int:id>/', reservadoDetalheEmpreendimento,
         name='reservado-detalhes-pre-reserva-lote'),
    path('listar_pre_reserva/', listaReservasTemporaria, name='lista-pre-reserva'),
    path('cancela_reserva_lote/<int:id>/', cancelarReservadoTemporaria, name='cancela-lote-pre-reserva'),
    path('cancela_reserva_lote_lista/<int:id>/', cancelarReservadoTemporariaLista,
         name='cancela-lote-pre-reserva-lista'),
    path('renova_reserva_lote/<int:id>/', renovaReserva, name='renova-lote-pre-reserva'),
    path('libera_lote/<int:id>/', liberaLote, name='libera-lote'),
    path('relatorio-lotes/', gerarRelatorioLotes, name='relatorio-lotes'),

]