from django.urls import path
from .views import contrato_view, contrato_pdf, proposta, proposta_pdf, contrato, contrato_pdf1

urlpatterns = [
    path('teste/', contrato_view, name='contrato_view'),
    path('pdf/', contrato_pdf, name='contrato_pdf'),
    path('proposta/<uuid:venda_uuid>/', proposta, name='proposta'),
    path('proposta/pdf/<uuid:venda_uuid>/', proposta_pdf, name='proposta_pdf'),
    path('contrato/<uuid:venda_uuid>/', contrato, name='contrato'),
    path('contrato/pdf/', contrato_pdf1, name='contrato_pdf'),
]
