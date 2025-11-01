from django.apps import AppConfig


class EmpreendimentosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empreendimentos'

    """def ready(self):
        import empreendimentos.signals
        import empreendimentos.signals_notificacao"""