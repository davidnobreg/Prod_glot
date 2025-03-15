from django.contrib import admin
from accounts.views import criarUsuario
from .models import RegisterVenda

@admin.register(RegisterVenda)
class RegisterVendaAdmin(admin.ModelAdmin):
    list_display = ['id', 'lote', 'cliente', 'tipo_venda', 'user', 'dt_reserva', 'dt_venda', 'create_at','is_ativo']
    search_fields = ['cliente__name', 'user__name']
