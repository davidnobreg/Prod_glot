from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'documento', 'email', 'fone', 'is_ativo']
