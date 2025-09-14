from django.contrib import admin
from empreendimentos import models
from accounts.models import UsuarioEmpreendimento
from django.contrib.auth import get_user_model

User = get_user_model()

# Inline Admin para as Quadras dentro de Empreendimento
class QuadraInlineAdmin(admin.TabularInline):
    model = models.Quadra
    extra = 0  # Não adicionar quadras vazias

# Admin para o modelo Empreendimento
class EmpreendimentoAdmin(admin.ModelAdmin):
    inlines = [QuadraInlineAdmin]  # Incluir Quadra como inline no Empreendimento
    list_display = ['id', 'nome', 'tempo_reserva', 'quantidade_parcela', 'is_ativo']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filtrando os empreendimentos pelos que estão vinculados ao usuário
        empreendimentos_ids = UsuarioEmpreendimento.objects.filter(
            usuario=request.user
        ).values_list('empreendimento_id', flat=True)
        return qs.filter(id__in=empreendimentos_ids)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return True
        return UsuarioEmpreendimento.objects.filter(usuario=request.user, empreendimento=obj).exists()

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return True
        return UsuarioEmpreendimento.objects.filter(usuario=request.user, empreendimento=obj).exists()

admin.site.register(models.Empreendimento, EmpreendimentoAdmin)


# Inline Admin para os Lotes dentro de Quadra
class LoteInlineAdmin(admin.TabularInline):
    model = models.Lote
    extra = 0  # Não adicionar lotes vazios
    fields = ['id', 'lote', 'area', 'situacao', 'data_termina_reserva']  # Definindo campos a serem exibidos

# Admin para o modelo Quadra
class QuadraAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "get_nome_empr", "get_tempo_reserva", "get_logo_empr"]  # Alteração dos campos para usar métodos
    inlines = [LoteInlineAdmin]  # Incluir Lote como inline dentro de Quadra

    # Métodos para acessar campos do modelo Empreendimento
    def get_nome_empr(self, obj):
        return obj.empr.nome  # Acessando 'nome' do modelo Empreendimento relacionado

    def get_tempo_reserva(self, obj):
        return obj.empr.tempo_reserva  # Acessando 'tempo_reserva' do modelo Empreendimento relacionado

    def get_logo_empr(self, obj):
        return obj.empr.logo.url if obj.empr.logo else None  # Acessando 'logo' do modelo Empreendimento relacionado

    get_nome_empr.short_description = 'Nome Empreendimento'  # Definindo o título do campo no admin
    get_tempo_reserva.short_description = 'Tempo de Reserva'  # Definindo o título do campo no admin
    get_logo_empr.short_description = 'Logo Empreendimento'  # Definindo o título do campo no admin

admin.site.register(models.Quadra, QuadraAdmin)


# Admin para o modelo Lote
class LoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'quadra', 'lote', 'area', 'situacao', 'tempo_reservado', 'valor_metro_quadrado']  # Exibir esses campos na lista de Lotes
    search_fields = ['lote']  # Permitir busca por 'lote'

admin.site.register(models.Lote, LoteAdmin)

# Admin para a tabela intermediária UsuarioEmpreendimento
class UsuarioEmpreendimentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_nome_usuario', 'usuario', 'empreendimento', 'ativo']
    search_fields = ['usuario__username', 'usuario__first_name', 'empreendimento__nome']

    # Método para exibir o nome completo do usuário no admin
    def get_nome_usuario(self, obj):
        return obj.usuario.get_full_name()  # Nome completo do usuário
    get_nome_usuario.short_description = 'Nome do Usuário'  # Título do campo no admin

admin.site.register(UsuarioEmpreendimento, UsuarioEmpreendimentoAdmin)
