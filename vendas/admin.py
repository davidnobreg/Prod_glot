from django.contrib import admin
from .models import RegisterVenda, RegisterVendaIntercalada


class RegisterVendaIntercaladaInline(admin.TabularInline):
    model = RegisterVendaIntercalada
    extra = 1

@admin.register(RegisterVenda)
class RegisterVendaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'lote', 'cliente', 'tipo_venda',
        'user', 'dt_reserva', 'dt_venda',
        'create_at', 'is_ativo', 'uuid'
    )

    search_fields = (
        'id',
        'uuid',
        'lote__id',
        'cliente__name',
        'user__username',
    )

    list_filter = (
        'tipo_venda',
        'is_ativo',
    )

    # aqui colocamos TODOS os inlines juntos
    inlines = [
        RegisterVendaIntercaladaInline
    ]