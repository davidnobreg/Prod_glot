from django.urls import path

from .views_documentos import (
    modelos_lista,
    modelo_editor,
    modelo_salvar,
    modelo_preview,
    modelo_duplicar,
    modelo_toggle_ativo,
    modelo_historico,
    variaveis_lista,
    empreendimento_margens_salvar,
)
from .views import (
    proposta,
    proposta_legado,
)
from .views_contratos import (
    contrato,
    contrato_pdf,
    proposta_pdf,
    proposta_rascunho,
    proposta_rascunho_pdf,
)
from .views_gerar import (
    gerar_documento,
    documento_detalhe,
    documento_finalizar,
    documento_status,
    documento_cancelar,
    documento_preview,
)

app_name = 'documentos'

urlpatterns = [
    path('modelos/', modelos_lista, name='modelos-lista'),
    path('modelos/novo/', modelo_editor, name='modelo-novo'),
    path('modelos/<int:pk>/', modelo_editor, name='modelo-editor'),
    path('modelos/<int:pk>/salvar/', modelo_salvar, name='modelo-salvar'),
    path('modelos/salvar/', modelo_salvar, name='modelo-salvar-novo'),
    path('modelos/<int:pk>/preview/', modelo_preview, name='modelo-preview'),
    path('modelos/<int:pk>/historico/', modelo_historico, name='modelo-historico'),
    path('modelos/<int:pk>/duplicar/', modelo_duplicar, name='modelo-duplicar'),
    path('modelos/<int:pk>/toggle-ativo/', modelo_toggle_ativo, name='modelo-toggle-ativo'),
    path('empreendimentos/<uuid:empreendimento_uuid>/margens/', empreendimento_margens_salvar, name='empreendimento-margens-salvar'),
    path('variaveis/', variaveis_lista, name='variaveis-lista'),
    path('proposta/<uuid:venda_uuid>/', proposta, name='proposta'),
    path('proposta/legado/<uuid:venda_uuid>/', proposta_legado, name='proposta-legado'),
    path('proposta/rascunho/<uuid:venda_uuid>/', proposta_rascunho, name='proposta-rascunho'),
    path('proposta/rascunho/pdf/<uuid:venda_uuid>/', proposta_rascunho_pdf, name='proposta-rascunho-pdf'),
    path('proposta/pdf/<uuid:venda_uuid>/', proposta_pdf, name='proposta_pdf'),
    path('contrato/<uuid:venda_uuid>/', contrato, name='contrato'),
    path('contrato/pdf/<uuid:venda_uuid>/', contrato_pdf, name='contrato_pdf'),

    path('gerar/<uuid:venda_uuid>/', gerar_documento, name='gerar-documento'),
    path('doc/<int:pk>/', documento_detalhe, name='documento-detalhe'),
    path('doc/<int:pk>/preview/', documento_preview, name='documento-preview'),
    path('doc/<int:pk>/finalizar/', documento_finalizar, name='documento-finalizar'),
    path('doc/<int:pk>/status/', documento_status, name='documento-status'),
    path('doc/<int:pk>/cancelar/', documento_cancelar, name='documento-cancelar'),
]
