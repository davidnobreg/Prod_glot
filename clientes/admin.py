from django.contrib import admin
from .models import Cliente

from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'documento_formatado', 'email', 'fone', 'is_ativo']
    search_fields = ('name', 'documento', 'email')
    list_filter = ('is_ativo',)

    def documento_formatado(self, obj):
        """Mostra CPF/CNPJ formatado na lista do admin."""
        doc = obj.documento
        if len(doc) == 11:
            return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
        elif len(doc) == 14:
            return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
        return doc

    documento_formatado.short_description = "CPF/CNPJ"
