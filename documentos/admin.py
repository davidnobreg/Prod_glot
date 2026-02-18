from django.contrib import admin
from .models import CadastroDocumento


@admin.register(CadastroDocumento)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'tipo', 'atualizado_em', 'ativo')
    list_filter = ('ativo','tipo',)
    search_fields = ('titulo',)