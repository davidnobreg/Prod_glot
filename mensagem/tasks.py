import logging
from celery import shared_task
from .services.n8n_service import N8nService

logger = logging.getLogger(__name__)


def enviar_mensagem(numero: str = None, mensagem: str = None, instancia: str = None):
    """
    Função helper reutilizável (shell, signal, Celery, Beat).
    """
    if not numero or not mensagem:
        logger.warning(
            "Nenhum número ou mensagem fornecido | numero=%s mensagem=%s instancia=%s",
            numero, mensagem, instancia
        )
        return None

    service = N8nService()
    resultado = service.enviar_mensagem(numero, mensagem, instancia)

    logger.info("Mensagem enviada para %s | Resultado=%s", numero, resultado)
    return resultado


@shared_task(bind=True, name="mensagem.tasks.enviar_mensagem_task")
def enviar_mensagem_task(self, numero=None, mensagem=None, instancia=None):
    """
    Task Celery segura para Signal, delay, apply_async e Beat.
    """
    logger.debug(
        "Executando enviar_mensagem_task | numero=%s mensagem=%s instancia=%s",
        numero, mensagem, instancia
    )

    return enviar_mensagem(numero, mensagem, instancia)
