
from django.urls import path

from .views import (
    # Empreendimento
    criarEmpreendimento,
    listaEmpreendimento,
    listaEmpreendimentoTabela,
    selectEmpreendimento,
    alteraEmpreendimento,
    deleteEmpreendimento,
    detalheEmpreendimento,

    # Importação
    importarDados,

    # Quadras e lotes
    listaQuadra,
    atualizarLotes,
    editarAtualizarLote,
    gerarRelatorioLotes,

    # Reserva / Pré-reserva
    alteraLote,
    reservadoDetalheEmpreendimento,
    listaReservasTemporaria,
    cancelarReservadoTemporaria,
    cancelarReservadoTemporariaLista,
    renovaReserva,
    liberaLote,

    # Relatórios
    relatorioFinanceiro,

    # Usuários / Corretores do empreendimento
    criarUsuarioEmpreendimento,
    deleteUsuarioEmpreendimento,

    # Modelos de documento
    modelo_vincular,
    modelo_desvincular,
    modelo_set_padrao,

    # Exportar / Importar lotes em massa
    exportar_lotes,
    importar_lotes,
    importar_lotes_confirmar,
)


urlpatterns = [
    # =========================
    # Empreendimentos
    # =========================
    path(
        '',
        listaEmpreendimento,
        name='lista-empreendimento'
    ),

    path(
        'insert_empreendimento/',
        criarEmpreendimento,
        name='criar-empreendimento'
    ),

    path(
        'listar_empreendimento/',
        listaEmpreendimentoTabela,
        name='lista-empreendimento-tabela'
    ),

    path(
        'select/<int:empreendimento_id>/',
        selectEmpreendimento,
        name='select-empreendimento'
    ),

    path(
        'alterar_empreendimento/<int:id>/',
        alteraEmpreendimento,
        name='alterar-empreendimento'
    ),

    path(
        'deleta_empreendimento/<int:empreendimento_Id>/',
        deleteEmpreendimento,
        name='deletar-empreendimento'
    ),

    path(
        'detalhe_empreendimento/<int:id>/',
        detalheEmpreendimento,
        name='detalhe-empreendimento'
    ),

    # =========================
    # Importação de dados
    # =========================
    path(
        'insert_arq/<int:id>/',
        importarDados.as_view(),
        name='arquivo'
    ),

    # =========================
    # Quadras e lotes
    # =========================
    path(
        'listar_quadras/<uuid:empreendimento_uuid>/',
        listaQuadra,
        name='listar-quadras'
    ),

    path(
        'atualizar-lotes/<uuid:empreendimento_uuid>/',
        atualizarLotes,
        name='atualizar-lotes'
    ),

    path(
        'atualizar-lotes/editar/<uuid:lote_uuid>/',
        editarAtualizarLote,
        name='editar-atualizar-lote'
    ),

    path(
        'relatorio-lotes/',
        gerarRelatorioLotes,
        name='relatorio-lotes'
    ),

    # =========================
    # Reserva / Pré-reserva
    # =========================
    path(
        'insert_reserva_pre_reserva_lote/<uuid:preReserva_uuid>/',
        reservadoDetalheEmpreendimento,
        name='reservado-detalhes-pre-reserva-lote'
    ),

    path(
        'listar_pre_reserva/',
        listaReservasTemporaria,
        name='lista-pre-reserva'
    ),

    path(
        'cancela_reserva_lote/<uuid:lote_uuid>/',
        cancelarReservadoTemporaria,
        name='cancela-lote-pre-reserva'
    ),

    path(
        'cancela_reserva_lote_lista/<uuid:lote_uuid>/',
        cancelarReservadoTemporariaLista,
        name='cancela-lote-pre-reserva-lista'
    ),

    path(
        'renova_reserva_lote/<uuid:renova_uuid>/',
        renovaReserva,
        name='renova-lote-pre-reserva'
    ),

    path(
        'libera_lote/<uuid:lote_uuid>/',
        liberaLote,
        name='libera-lote'
    ),

    # Esta rota está importada no seu arquivo original.
    # Mantenha se estiver sendo usada em algum template.
    path(
        'alterar_lote/<int:id>/',
        alteraLote,
        name='alterar-lote'
    ),

    # =========================
    # Relatórios
    # =========================
    path(
        'relatorio_financeiro/<int:id>/',
        relatorioFinanceiro,
        name='relatorio-financeiro'
    ),

    # =========================
    # Usuários / Corretores do empreendimento
    # =========================
    path(
        'usuariosempreendimento/',
        criarUsuarioEmpreendimento,
        name='criar-usuario-empreendimento'
    ),

    path(
        'usuariosempreendimento/<int:id>/delete/',
        deleteUsuarioEmpreendimento,
        name='delete-usuario-empreendimento'
    ),

    # =========================
    # Modelos de documento
    # =========================
    path(
        'empreendimento/<int:empr_id>/modelo/vincular/',
        modelo_vincular,
        name='modelo-vincular'
    ),

    path(
        'empreendimento/<int:empr_id>/modelo/<int:vinculo_id>/desvincular/',
        modelo_desvincular,
        name='modelo-desvincular'
    ),

    path(
        'empreendimento/<int:empr_id>/modelo/<int:vinculo_id>/padrao/',
        modelo_set_padrao,
        name='modelo-set-padrao'
    ),

    # =========================
    # Exportar / Importar lotes em massa
    # =========================
    path(
        'detalhe_empreendimento/<int:empreendimento_id>/lotes/exportar/',
        exportar_lotes,
        name='exportar-lotes',
    ),
    path(
        'detalhe_empreendimento/<int:empreendimento_id>/lotes/importar/',
        importar_lotes,
        name='importar-lotes',
    ),
    path(
        'detalhe_empreendimento/<int:empreendimento_id>/lotes/importar/confirmar/',
        importar_lotes_confirmar,
        name='importar-lotes-confirmar',
    ),
]