from django.apps import AppConfig


class MensagemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mensagem'
    verbose_name = 'Sistema de Notificações'

    def ready(self):
        import mensagem.signals
