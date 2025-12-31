import requests
from celery import shared_task
from .services.n8n_service import N8nService

def enviar_mensagem(numero: str = None, mensagem: str = None, instancia: str = None):
    """
    Função helper para enviar mensagem direto no shell, via signal ou Celery.
    Se chamada sem argumentos (ex: Beat), apenas loga e não quebra.
    """
    if not numero or not mensagem:
        print("Nenhum número ou mensagem fornecido, task não enviará nada.")
        return None

    service = N8nService()
    resultado = service.enviar_mensagem(numero, mensagem, instancia)

    print(f"Mensagem enviada para {numero}")
    print("Resultado:", resultado)
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
def enviar_mensagem_task(self, numero: str = None, mensagem: str = None, instancia: str = None):
    """
    Task Celery para enviar mensagem usando N8nService.
    Pode ser chamada via delay, apply_async, signal ou Beat.
    """
    return enviar_mensagem(numero, mensagem, instancia)