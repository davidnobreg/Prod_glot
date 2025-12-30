from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import admin
from .models import Mensagem
from .tasks import enviar_mensagem_task

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("numero", "mensagem", "instancia", "enviado", "acao_enviar")

    def acao_enviar(self, obj):
        return format_html(
            '<a class="button" href="{}">Enviar Agora</a>',
            f"/admin/mensagem/mensagem/{obj.id}/enviar/"
        )
    acao_enviar.short_description = "Enviar"
    acao_enviar.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:mensagem_id>/enviar/', self.admin_site.admin_view(self.enviar_acao))
        ]
        return custom_urls + urls

    def enviar_acao(self, request, mensagem_id):
        obj = self.get_object(request, mensagem_id)
        if obj.numero and obj.mensagem:
            enviar_mensagem_task.delay(obj.numero, obj.mensagem, obj.instancia)
        self.message_user(request, "Mensagem enviada!")
        return redirect(f"/admin/mensagem/mensagem/")
