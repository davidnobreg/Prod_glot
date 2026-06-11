from django.urls import path
from .views import (
    proposta,
    proposta_legado,
    propostaRascunho,
    proposta_pdf,
    contrato,
    contrato_pdf1,
    upload_documento,
    preview_documento,
    marcadores_disponiveis,
)

urlpatterns = [

    path('proposta/<uuid:venda_uuid>/', proposta, name='proposta'),
    path('proposta/legado/<uuid:venda_uuid>/', proposta_legado, name='proposta-legado'),
    path('proposta_rascunho/<uuid:venda_uuid>/', propostaRascunho, name='proposta-rascunho'),
    path('proposta/pdf/<uuid:venda_uuid>/', proposta_pdf, name='proposta_pdf'),
    path('contrato/<uuid:venda_uuid>/', contrato, name='contrato'),
    path('contrato/pdf/', contrato_pdf1, name='contrato_pdf'),
    path('upload/', upload_documento, name='upload-documento'),
    path('upload/preview/', preview_documento, name='preview-documento'),
    path('marcadores/', marcadores_disponiveis, name='marcadores-disponiveis'),
]
