from django.contrib import admin
from .models import Cliente, ClienteTelefone


class ClienteTelefoneInline(admin.TabularInline):
	model = ClienteTelefone
	extra = 1


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

	list_display = ['id', 'name', 'documento', 'email', 'is_ativo']
	search_fields = ['name', 'documento', 'email']
	list_filter = ['estado_civil', 'is_ativo', 'nacionalidade']

	inlines = [
		ClienteTelefoneInline,
	]
