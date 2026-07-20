from django.contrib import admin
from .models import (
    RegisterVenda,
    RegisterVendaIntercalada,
    TransferenciaTitularidade,
    HistoricoTitularidade,
)


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


@admin.register(TransferenciaTitularidade)
class TransferenciaTitularidadeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'venda', 'cliente_anterior', 'cliente_novo',
        'status', 'iniciado_por', 'iniciado_em', 'efetivado_em',
    )
    list_filter = ('status',)
    search_fields = ('uuid', 'venda__id', 'cliente_anterior__name', 'cliente_novo__name')


@admin.register(HistoricoTitularidade)
class HistoricoTitularidadeAdmin(admin.ModelAdmin):
    list_display = ('id', 'venda', 'cliente', 'dt_inicio', 'dt_fim', 'transferencia_origem')
    list_filter = ('dt_fim',)
    search_fields = ('venda__id', 'cliente__name')