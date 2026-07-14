
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

    # Wizard de cadastro de empreendimento
    wizard_step1,
    wizard_step2,
    wizard_step3,
    wizard_step4,
    wizard_step5,
    wizard_step6,
    wizard_representante_del,
    wizard_rep_doc_upload,
    wizard_rep_doc_remover,
    wizard_doc_empreendimento_upload,
    wizard_doc_empreendimento_remover,

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

from . import views_update


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
        'select/<uuid:empreendimento_uuid>/',
        selectEmpreendimento,
        name='select-empreendimento'
    ),

    path(
        'alterar_empreendimento/<uuid:uuid>/',
        alteraEmpreendimento,
        name='alterar-empreendimento'
    ),

    path(
        'deleta_empreendimento/<uuid:empreendimento_uuid>/',
        deleteEmpreendimento,
        name='deletar-empreendimento'
    ),

    path(
        'detalhe_empreendimento/<uuid:uuid>/',
        detalheEmpreendimento,
        name='detalhe-empreendimento'
    ),

    # =========================
    # Wizard de cadastro de Empreendimento
    # =========================
    path('cadastrar/step1/', wizard_step1, name='empreendimento_wizard_step1'),
    path('cadastrar/step2/', wizard_step2, name='empreendimento_wizard_step2'),
    path('cadastrar/step3/', wizard_step3, name='empreendimento_wizard_step3'),
    path('cadastrar/step4/', wizard_step4, name='empreendimento_wizard_step4'),
    path(
        'cadastrar/step4/representante/<uuid:representante_uuid>/del/',
        wizard_representante_del,
        name='empreendimento_wizard_representante_del'
    ),
    path(
        'cadastrar/step4/representante/<uuid:rep_uuid>/documento/upload/',
        wizard_rep_doc_upload,
        name='wizard_rep_doc_upload'
    ),
    path(
        'cadastrar/step4/representante/documento/<uuid:doc_uuid>/remover/',
        wizard_rep_doc_remover,
        name='wizard_rep_doc_remover'
    ),
    path('cadastrar/step5/', wizard_step5, name='empreendimento_wizard_step5'),
    path('cadastrar/step6/', wizard_step6, name='empreendimento_wizard_step6'),
    path(
        'cadastrar/step6/documento/upload/',
        wizard_doc_empreendimento_upload,
        name='wizard_doc_empreendimento_upload'
    ),
    path(
        'cadastrar/step6/documento/<uuid:doc_uuid>/remover/',
        wizard_doc_empreendimento_remover,
        name='wizard_doc_empreendimento_remover'
    ),

    # =========================
    # Wizard de update de Empreendimento
    # =========================
    path(
        'editar/<uuid:empreendimento_uuid>/step1/',
        views_update.wizard_update_step1,
        name='empreendimento_update_step1'
    ),

    path(
        'editar/<uuid:empreendimento_uuid>/step2/',
        views_update.wizard_update_step2,
        name='empreendimento_update_step2'
    ),

    path(
        'editar/<uuid:empreendimento_uuid>/step3/',
        views_update.wizard_update_step3,
        name='empreendimento_update_step3'
    ),

    path(
        'editar/<uuid:empreendimento_uuid>/cancelar/',
        views_update.wizard_update_cancelar,
        name='wizard_update_cancelar'
    ),

    # =========================
    # Importação de dados
    # =========================
    path(
        'insert_arq/<uuid:uuid>/',
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
        'alterar_lote/<uuid:uuid>/',
        alteraLote,
        name='alterar-lote'
    ),

    # =========================
    # Relatórios
    # =========================
    path(
        'relatorio_financeiro/<uuid:uuid>/',
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
        'usuariosempreendimento/<uuid:usuario_empreendimento_uuid>/delete/',
        deleteUsuarioEmpreendimento,
        name='delete-usuario-empreendimento'
    ),

    # =========================
    # Modelos de documento
    # =========================
    path(
        'empreendimento/<uuid:empreendimento_uuid>/modelo/vincular/',
        modelo_vincular,
        name='modelo-vincular'
    ),

    path(
        'empreendimento/<uuid:empreendimento_uuid>/modelo/<uuid:vinculo_uuid>/desvincular/',
        modelo_desvincular,
        name='modelo-desvincular'
    ),

    path(
        'empreendimento/<uuid:empreendimento_uuid>/modelo/<uuid:vinculo_uuid>/padrao/',
        modelo_set_padrao,
        name='modelo-set-padrao'
    ),

    # =========================
    # Exportar / Importar lotes em massa
    # =========================
    path(
        'detalhe_empreendimento/<uuid:empreendimento_uuid>/lotes/exportar/',
        exportar_lotes,
        name='exportar-lotes',
    ),
    path(
        'detalhe_empreendimento/<uuid:empreendimento_uuid>/lotes/importar/',
        importar_lotes,
        name='importar-lotes',
    ),
    path(
        'detalhe_empreendimento/<uuid:empreendimento_uuid>/lotes/importar/confirmar/',
        importar_lotes_confirmar,
        name='importar-lotes-confirmar',
    ),
]