from django.contrib import admin
from accounts.views import criar_usuario
from .models import RegisterVenda

@admin.register(RegisterVenda)
class RegisterVendaAdmin(admin.ModelAdmin):
    list_display = ['id', 'lote', 'cliente', 'tipo_venda', 'user', 'dt_reserva', 'dt_venda', 'create_at','is_ativo']

