"""URLs do módulo de documentos reestruturado (namespace 'documentos').

Módulo separado do urls.py legado para não namespacear as URLs antigas
(proposta, upload-documento, etc.) que são referenciadas sem namespace.
"""
from django.urls import path

from . import views_documentos as v

app_name = 'documentos'

urlpatterns = [
	# Modelos
	path('modelos/', v.modelos_lista, name='modelos-lista'),
	path('modelos/novo/', v.modelo_editor, name='modelo-novo'),
	path('modelos/salvar/', v.modelo_salvar, name='modelo-salvar-novo'),
	path('modelos/<int:pk>/editar/', v.modelo_editor, name='modelo-editar'),
	path('modelos/<int:pk>/salvar/', v.modelo_salvar, name='modelo-salvar'),
	path('modelos/<int:pk>/duplicar/', v.modelo_duplicar, name='modelo-duplicar'),
	path('modelos/<int:pk>/toggle-ativo/', v.modelo_toggle_ativo, name='modelo-toggle-ativo'),
	path('modelos/<int:pk>/preview/', v.modelo_preview, name='modelo-preview'),
	path('modelos/<int:pk>/historico/', v.modelo_historico, name='modelo-historico'),

	# Geração / documentos
	path('gerar/venda/<int:venda_pk>/', v.gerar_documento, name='gerar-documento'),
	path('doc/<int:pk>/', v.documento_detalhe, name='documento-detalhe'),
	path('doc/<int:pk>/finalizar/', v.documento_finalizar, name='documento-finalizar'),
	path('doc/<int:pk>/status/', v.documento_status, name='documento-status'),
	path('doc/<int:pk>/substituir/', v.documento_substituir, name='documento-substituir'),
	path('doc/<int:pk>/cancelar/', v.documento_cancelar, name='documento-cancelar'),
	path('doc/<int:pk>/pdf/', v.documento_pdf, name='documento-pdf'),

	# Distratos
	path('distratos/novo/venda/<int:venda_pk>/', v.distrato_novo, name='distrato-novo'),
	path('distratos/<int:pk>/', v.distrato_detalhe, name='distrato-detalhe'),
	path('distratos/<int:pk>/concluir/', v.distrato_concluir, name='distrato-concluir'),

	# Variáveis
	path('variaveis/', v.variaveis_lista, name='variaveis-lista'),
]
