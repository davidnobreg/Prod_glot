from django.urls import path
from .views import contrato_view, contrato_pdf

urlpatterns = [
    path('teste/', contrato_view, name='contrato_view'),
    path('pdf/', contrato_pdf, name='contrato_pdf'),
]
