from django.contrib import admin
from .models import Cliente, ClienteConjuge, ClienteEndereco, ClienteTelefone


class ClienteEnderecoInline(admin.StackedInline):
    model = ClienteEndereco
    extra = 0
    max_num = 1


class ClienteConjugeInline(admin.StackedInline):
    model = ClienteConjuge
    extra = 0
    max_num = 1


class ClienteTelefoneInline(admin.TabularInline):
    model = ClienteTelefone
    extra = 1


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

    list_display = ['id', 'name', 'documento', 'email', 'is_ativo']
    search_fields = ['name', 'documento', 'email']
    list_filter = ['estado_civil', 'is_ativo', 'nacionalidade']

    list_display = ['id', 'name', 'documento', 'email', 'is_ativo']
    search_fields = ('name', 'documento', 'email')
    list_filter = ('is_ativo',)


    # aqui colocamos TODOS os inlines juntos
    inlines = [
        ClienteEnderecoInline,
        ClienteConjugeInline,
        ClienteTelefoneInline,
    ]
