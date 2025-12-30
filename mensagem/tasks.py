from celery import shared_task
from .services.n8n_service import N8nService

def enviar_mensagem(numero: str, mensagem: str, instancia: str = None):
    """
    Função helper para enviar mensagem direto no shell ou em outras funções Python.
    """
    service = N8nService()
    resultado = service.enviar_mensagem(numero, mensagem, instancia)

    print(f"Mensagem enviada para {numero}")
    print("Resultado:", resultado)
    return resultado


@shared_task(bind=True, name="mensagem.tasks.enviar_mensagem_task")
def enviar_mensagem_task(self, numero: str, mensagem: str, instancia: str = None):
    """
    Task Celery para enviar mensagem usando N8nService.
    Pode ser chamada via delay ou apply_async.
    """
    return enviar_mensagem(numero, mensagem, instancia)

