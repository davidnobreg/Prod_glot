from django.urls import path
from .views import (criarEmpreendimento, listaEmpreendimento, listaEmpreendimentoTabela, listaQuadra, \
                    deleteEmpreendimento, alteraEmpreendimento, selectEmpreendimento, detalheEmpreendimento,
                    relatorioFinanceiro, reservadoDetalheEmpreendimento, listaReservasTemporaria,
                    cancelarReservadoTemporaria, cancelarReservadoTemporariaLista, \
                    alteraLote, renovaReserva, liberaLote, gerarRelatorioLotes, criarUsuarioEmpreendimento, \
                    importarDados, atualizarLotes, editarAtualizarLote)

urlpatterns = [
    # Cadastro de cliente
    path('insert_empreendimento/', criarEmpreendimento, name='criar-empreendimento'),

    path('select/<int:empreendimento_id>/', selectEmpreendimento, name='select-empreendimento'),

    path('alterar_empreendimento/<int:id>/', alteraEmpreendimento, name='alterar-empreendimento'),

    path('deleta_empreendimento/<int:empreendimento_Id>/', deleteEmpreendimento, name='deletar-empreendimento'),

    path('insert_arq/<int:id>/', importarDados.as_view(), name='arquivo'),

    path('', listaEmpreendimento, name='lista-empreendimento'),

    path('listar_empreendimento/', listaEmpreendimentoTabela, name='lista-empreendimento-tabela'),

    path('listar_quadras/<uuid:empreendimento_uuid>/', listaQuadra, name='listar-quadras'),

    path('detalhe_empreendimento/<int:id>/', detalheEmpreendimento, name='detalhe-empreendimento'),

    path('relatorio_financeiro/<int:id>/', relatorioFinanceiro, name='relatorio-financeiro'),

    path('insert_reserva_pre_reserva_lote/<uuid:preReserva_uuid>/', reservadoDetalheEmpreendimento,
         name='reservado-detalhes-pre-reserva-lote'),
    path('listar_pre_reserva/', listaReservasTemporaria, name='lista-pre-reserva'),
    path('cancela_reserva_lote/<uuid:lote_uuid>/', cancelarReservadoTemporaria, name='cancela-lote-pre-reserva'),
    path('cancela_reserva_lote_lista/<uuid:lote_uuid>/', cancelarReservadoTemporariaLista,
         name='cancela-lote-pre-reserva-lista'),
    path('renova_reserva_lote/<uuid:renova_uuid>/', renovaReserva, name='renova-lote-pre-reserva'),
    path('libera_lote/<uuid:lote_uuid>/', liberaLote, name='libera-lote'),
    path('relatorio-lotes/', gerarRelatorioLotes, name='relatorio-lotes'),
    path('atualizar-lotes/<uuid:empreendimento_uuid>/', atualizarLotes, name='atualizar-lotes'),
    path('atualizar-lotes/editar/<uuid:lote_uuid>/', editarAtualizarLote, name='editar-atualizar-lote'),

    path('usuariosempreendimento/', criarUsuarioEmpreendimento, name='criar-usuario-empreendimento'),


]
