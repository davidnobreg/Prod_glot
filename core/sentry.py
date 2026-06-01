import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

def init_sentry(dsn: str, environment: str = "production", release: str = None):
    """
    Inicializa o Sentry com todas as integrações do GLOT.
    Chamar esta função no settings.py de produção.
    """

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,

        integrations=[
            # Captura erros do Django (views, templates, signals)
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
                signals_spans=False,
            ),

            # Captura erros do Celery (workers e beat)
            CeleryIntegration(
                monitor_beat_tasks=True,
            ),

            # Captura logs de ERROR e CRITICAL como eventos no Sentry
            LoggingIntegration(
                level=logging.ERROR,
                event_level=logging.ERROR,
            ),
        ],

        # % de transações monitoradas para performance (0.0 = desligado)
        traces_sample_rate=0.1,

        # Não envia dados sensíveis
        send_default_pii=False,

        # Ignora erros irrelevantes para não gastar a cota
        ignore_errors=[
            "Http404",
            "PermissionDenied",
            "django.security.DisallowedHost",
        ],
    )