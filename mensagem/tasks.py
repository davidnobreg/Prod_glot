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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def enviar_mensagem_task(self, numero: str = None, mensagem: str = None, instancia: str = None):
    """
    Task Celery segura para Signal, delay, apply_async e Beat.
    """

    # 🔒 Validação forte (não faz retry)
    if not numero or not mensagem:
        logger.warning(
            f"🚫 Parâmetros inválidos: numero={numero}, mensagem={mensagem}"
        )
        return {
            "success": False,
            "error": "Parâmetros inválidos"
        }

    try:
        resultado = enviar_mensagem(numero, mensagem, instancia)

        # ✅ SUCESSO REAL (flexível)
        if (
            resultado.get("success") is True
            or resultado.get("status") in (200, 201)
        ):
            logger.info(
                f"✅ Mensagem enviada para {numero} | Resultado={resultado}"
            )
            return resultado

        # ❌ ERRO REAL (API respondeu, mas falhou)
        raise Exception(f"Falha no envio: {resultado}")

    except ConnectionError as e:
        # 🌐 erro transitório → retry
        logger.error(f"🌐 Erro de conexão ao enviar para {numero}: {e}")
        raise self.retry(exc=e)

    except TimeoutError as e:
        # ⏱ erro transitório → retry
        logger.error(f"⏱ Timeout ao enviar para {numero}: {e}")
        raise self.retry(exc=e)

    except Exception as e:
        # ❌ erro definitivo → NÃO retry infinito
        logger.error(f"❌ Erro definitivo ao enviar para {numero}: {e}")
        raise
