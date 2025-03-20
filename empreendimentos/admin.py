from django.contrib import admin
from empreendimentos import models


# Inline Admin para as Quadras dentro de Empreendimento
class QuadraInlineAdmin(admin.TabularInline):
    model = models.Quadra
    extra = 0  # Não adicionar quadras vazias

# Admin para o modelo Empreendimento
class EmpreendimentoAdmin(admin.ModelAdmin):
    inlines = [QuadraInlineAdmin]  # Incluir Quadra como inline no Empreendimento

admin.site.register(models.Empreendimento, EmpreendimentoAdmin)


# Inline Admin para os Lotes dentro de Quadra
class LoteInlineAdmin(admin.TabularInline):
    model = models.Lote
    extra = 0  # Não adicionar lotes vazios
    fields = ['id', 'lote', 'area', 'situacao']  # Definindo campos a serem exibidos

# Admin para o modelo Quadra
class QuadraAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "get_nome_empr", "get_tempo_reserva", "get_logo_empr"]  # Alteração dos campos para usar métodos
    inlines = [LoteInlineAdmin]  # Incluir Lote como inline dentro de Quadra

    # Métodos para acessar campos do modelo Empreendimento
    def get_nome_empr(self, obj):
        return obj.empr.nome  # Acessando 'nome' do modelo Empreendimento relacionado

    def get_tempo_reserva(self, obj):
        return obj.empr.tempo_reseva  # Acessando 'tempo_reseva' do modelo Empreendimento relacionado

    def get_logo_empr(self, obj):
        return obj.empr.logo.url if obj.empr.logo else None  # Acessando 'logo' do modelo Empreendimento relacionado

    get_nome_empr.short_description = 'Nome Empreendimento'  # Definindo o título do campo no admin
    get_tempo_reserva.short_description = 'Tempo de Reserva'  # Definindo o título do campo no admin
    get_logo_empr.short_description = 'Logo Empreendimento'  # Definindo o título do campo no admin

admin.site.register(models.Quadra, QuadraAdmin)


# Admin para o modelo Lote
class LoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'lote', 'area', 'situacao']  # Exibir esses campos na lista de Lotes
    search_fields = ['lote']  # Permitir busca por 'lote'

admin.site.register(models.Lote, LoteAdmin)
