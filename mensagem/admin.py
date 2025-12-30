from django.contrib import admin
from .models import Mensagem  # supondo que você tenha um model para registrar mensagens
from .tasks import enviar_mensagem_task

@admin.action(description="Enviar mensagens selecionadas via N8n")
def enviar_mensagens(modeladmin, request, queryset):
    for obj in queryset:
        # supondo que o model tenha campos numero, mensagem e instancia
        numero = obj.numero
        mensagem = obj.mensagem
        instancia = obj.instancia
        if numero and mensagem:
            enviar_mensagem_task.delay(numero, mensagem, instancia)
    modeladmin.message_user(request, "Mensagens enviadas!")

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("numero", "mensagem", "instancia", "enviado")
    actions = [enviar_mensagens]
