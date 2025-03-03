from django.contrib import admin
from empreendimentos import models

class QuadraInlineAdmin(admin.TabularInline):
    model = models.Quadra
    extra = 0

class QuadraAdmin(admin.ModelAdmin):
    inlines = [QuadraInlineAdmin]
 
admin.site.register(models.Empreendimento, QuadraAdmin)

class LoteInlineAdmin(admin.TabularInline):
    model = models.Lote
    extra = 0

class LoteAdmin(admin.ModelAdmin):
    inlines = [LoteInlineAdmin]

admin.site.register(models.Quadra, LoteAdmin)

admin.site.register(models.Lote)
