from django.contrib import admin
from .models import Cliente, ClienteDocumento, ClienteTelefone


class ClienteTelefoneInline(admin.TabularInline):
	model = ClienteTelefone
	extra = 1


class ClienteDocumentoInline(admin.TabularInline):
	model = ClienteDocumento
	extra = 0
	readonly_fields = ['criado_em']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

	list_display = ['id', 'name', 'documento', 'email', 'is_ativo']
	search_fields = ['name', 'documento', 'email']
	list_filter = ['estado_civil', 'is_ativo', 'nacionalidade']

	inlines = [
		ClienteTelefoneInline,
		ClienteDocumentoInline,
	]
