from django.contrib import admin

from .models import (
	VariavelDocumento,
	ModeloDocumento,
	ModeloDocumentoHistorico,
	EmpreendimentoDocumento,
	ConfiguracaoDocumento,
	SequencialDocumento,
	DocumentoGerado,
)


@admin.register(VariavelDocumento)
class VariavelDocumentoAdmin(admin.ModelAdmin):
	list_display = ('tag_slug', 'label', 'categoria', 'exemplo', 'ativo', 'ordem')
	list_filter = ('categoria', 'ativo')
	search_fields = ('tag_slug', 'label')
	ordering = ('categoria', 'ordem', 'label')


@admin.register(ModeloDocumento)
class ModeloDocumentoAdmin(admin.ModelAdmin):
	list_display = ('id', 'titulo', 'tipo', 'eh_global', 'versao', 'ativo', 'atualizado_em')
	list_filter = ('tipo', 'eh_global', 'ativo')
	search_fields = ('titulo',)


@admin.register(ModeloDocumentoHistorico)
class ModeloDocumentoHistoricoAdmin(admin.ModelAdmin):
	list_display = ('modelo', 'versao', 'editado_por', 'editado_em')
	list_filter = ('editado_em',)
	search_fields = ('modelo__titulo',)


@admin.register(EmpreendimentoDocumento)
class EmpreendimentoDocumentoAdmin(admin.ModelAdmin):
	list_display = ('empreendimento', 'modelo', 'padrao', 'ativo', 'ordem')
	list_filter = ('padrao', 'ativo')
	search_fields = ('empreendimento__nome', 'modelo__titulo')


@admin.register(ConfiguracaoDocumento)
class ConfiguracaoDocumentoAdmin(admin.ModelAdmin):
	list_display = ('empreendimento', 'fonte_familia', 'fonte_tamanho')
	search_fields = ('empreendimento__nome',)


@admin.register(SequencialDocumento)
class SequencialDocumentoAdmin(admin.ModelAdmin):
	list_display = ('tipo', 'ano', 'ultimo')
	list_filter = ('tipo', 'ano')


@admin.register(DocumentoGerado)
class DocumentoGeradoAdmin(admin.ModelAdmin):
	list_display = ('numero', 'titulo', 'status', 'modelo', 'venda', 'criado_por', 'criado_em')
	list_filter = ('status', 'criado_em')
	search_fields = ('numero', 'titulo')
	readonly_fields = ('numero', 'hash_conteudo', 'finalizado_em')
