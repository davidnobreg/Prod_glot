# mensagem/tasks.py

import logging
from celery import shared_task
from celery.exceptions import Reject

from .services.n8n_service import N8nService

logger = logging.getLogger(__name__)


# ==========================================================
# FUNÇÃO HELPER (REUTILIZÁVEL)
# ==========================================================

def enviar_mensagem(numero: str, mensagem: str, instancia: str = None):
    """
    Função helper reutilizável:
    - Django shell
    - Signals
    - Celery
    - Views / Services
    """

    if not numero or not mensagem:
<<<<<<< Updated upstream
        logger.warning(
            "Nenhum número ou mensagem fornecido | numero=%s mensagem=%s instancia=%s",
            numero, mensagem, instancia
        )
        return None
=======
        raise ValueError("Número e mensagem são obrigatórios")
>>>>>>> Stashed changes

    service = N8nService()

    # 🔐 timeout obrigatório para não travar worker
    resultado = service.enviar_mensagem(
        numero=numero,
        mensagem=mensagem,
        instancia=instancia,
        timeout=10,  # segundos
    )

    logger.info(
        "📨 Mensagem enviada | numero=%s instancia=%s resultado=%s",
        numero, instancia, resultado
    )

    return resultado


<<<<<<< Updated upstream
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
=======
# ==========================================================
# TASK CELERY — ENVIO DE MENSAGEM
# ==========================================================

@shared_task(
    bind=True,
    name="mensagem.tasks.enviar_mensagem_task",
    queue="app_mensagem.default",
    routing_key="mensagem",
    autoretry_for=(requests.RequestException,),
    retry_kwargs={
        "max_retries": 3,
        "countdown": 30,
    },
    retry_backoff=True,
    retry_jitter=True,
    acks_late=True,
)
def enviar_mensagem_task(self, numero: str, mensagem: str, instancia: str = None):
    """
    Task Celery responsável EXCLUSIVAMENTE por envio de mensagens.
    - Assinatura explícita
    - Retry apenas para erro de rede
    - Falha rápida para erro lógico
    """

    logger.debug(
        "🔔 [CELERY] enviar_mensagem_task | numero=%s instancia=%s",
        numero, instancia
    )

    # ❌ Erro lógico → NÃO RETENTAR → NÃO DLQ
    if not numero or not mensagem:
        logger.error(
            "❌ Task chamada com parametros inválidos | numero=%s mensagem=%s",
            numero, mensagem
        )
        raise Reject("Parametros obrigatorios ausentes", requeue=False)

    try:
        return enviar_mensagem(numero, mensagem, instancia)

    except requests.RequestException as exc:
        # 🔁 Erro de rede → retry automático
        logger.warning(
            "🌐 Erro de rede ao enviar mensagem | tentativa=%s/%s",
            self.request.retries + 1,
            self.max_retries,
        )
        raise exc

    except Exception as exc:
        # ❌ Erro inesperado → NÃO retry → vai para DLQ
        logger.exception("💥 Erro inesperado ao enviar mensagem")
        raise Reject(str(exc), requeue=False)
>>>>>>> Stashed changes
