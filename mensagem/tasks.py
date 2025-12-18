import logging
from celery import shared_task
from django.conf import settings
from .services import EvolutionService

logger = logging.getLogger(__name__)


def get_evolution_service():
    """
    Cria a instância do serviço somente quando a task roda.
    Evita problemas de fork/spawn no Windows.
    """
    return EvolutionService(
        server_url=settings.EVOLUTION_URL,
        instance=settings.EVOLUTION_INSTANCE,
        api_key=settings.EVOLUTION_TOKEN
    )


@shared_task(
    bind=True,
    queue = "whatsapp",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
    retry_jitter=True
)

def enviar_mensagem_task(self, numero: str, mensagem: str, options: dict | None = None):
    """
    Task responsável por enviar mensagem via WhatsApp
    usando o Evolution API.
    """
    logger.info(f"📤 Enviando mensagem para {numero}")

    service = get_evolution_service()

    resultado = service.enviar_mensagem(
        numero=numero,
        mensagem=mensagem,
        options=options
    )

    if not resultado or not resultado.get("success"):
        erro = resultado.get("error", "Erro desconhecido")
        logger.error(f"❌ Falha no envio para {numero}: {erro}")

        # APENAS lança exceção
        # O Celery faz o retry automaticamente
        raise Exception(erro)

    logger.info(f"✅ Mensagem enviada com sucesso para {numero}")
    return resultado


@shared_task
def enviar_mensagem_whatsapp_agendada():
    """
    Task simples para envio automático/agendado
    """
    return enviar_mensagem_task.delay(
        numero=settings.WHATSAPP_NUMERO_PADRAO,
        mensagem="Mensagem automática do sistema",
        options={"delay": 5}
    )
