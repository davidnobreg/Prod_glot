from django.contrib import admin
from clientes import models

#@admin.register(id, name, documento, email, fone, is_ativo)
# Register your models here.
admin.site.register(models.Cliente)
    #list_display = ["id", "name", "documento"]