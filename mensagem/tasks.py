import logging
import requests
from celery import shared_task
from .services.n8n_service import N8nService

logger = logging.getLogger(__name__)


def enviar_mensagem(numero: str = None, mensagem: str = None, instancia: str = None):
    """
    Função helper reutilizável (shell, signal, Celery, Beat).
    """
    if not numero or not mensagem:
        logger.warning(
            "Nenhum número ou mensagem fornecido. "
            "numero=%s mensagem=%s instancia=%s",
            numero, mensagem, instancia
        )
        return None

    service = N8nService()
    resultado = service.enviar_mensagem(numero, mensagem, instancia)

    logger.info("Mensagem enviada para %s | Resultado=%s", numero, resultado)
    return resultado



@shared_task(
    bind=True,
    name="mensagem.tasks.enviar_mensagem_task",
    queue="app_mensagem.default",
    routing_key="mensagem",
    autoretry_for=(requests.RequestException,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
    retry_backoff=True,
    retry_jitter=True,
)
def enviar_mensagem_task(self, *args, **kwargs):
    """
    Task Celery BLINDADA para Beat, delay, apply_async e signals.
    """

    # 🔐 Extrai somente o que importa (Beat SEMPRE manda kwargs)
    numero = kwargs.get("numero")
    mensagem = kwargs.get("mensagem")
    instancia = kwargs.get("instancia")

    print(mumero, mensagem, instancia)

    logger.debug(
        "Executando enviar_mensagem_task | args=%s kwargs=%s",
        args, kwargs
    )

    return enviar_mensagem(numero, mensagem, instancia)
