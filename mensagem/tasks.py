from celery import shared_task
from .services import EvolutionService
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

evolution_service = EvolutionService(
    server_url=settings.EVOLUTION_URL,
    instance=settings.EVOLUTION_INSTANCE,
    api_key=settings.EVOLUTION_TOKEN
)

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def enviar_mensagem_task(self, numero, mensagem, options=None):
    try:
        resultado = evolution_service.enviar_mensagem(numero, mensagem, options)
        if not resultado.get("success"):
            raise Exception(f"Falha no envio: {resultado}")
        return resultado
    except Exception as e:
        logger.error(f"❌ Exceção ao enviar mensagem para {numero}: {e}")
        raise self.retry(exc=e)
