# mensagem/tasks.py

import logging

from celery import shared_task

from .services.n8n_service import N8nService

logger = logging.getLogger(__name__)


def enviar_mensagem(numero: str, mensagem: str, instancia: str = None):
	"""
	Helper reutilizavel para shell, signals, Celery, views e services.
	"""
	if not numero or not mensagem:
		raise ValueError("Numero e mensagem sao obrigatorios")

	service = N8nService()
	resultado = service.enviar_mensagem(
		numero=numero,
		mensagem=mensagem,
		instancia=instancia,
		timeout=10,
	)

	logger.info(
		"Mensagem enviada | numero=%s instancia=%s resultado=%s",
		numero,
		instancia,
		resultado,
	)

	return resultado


@shared_task(
	bind=True,
	name="mensagem.tasks.enviar_mensagem_task",
	autoretry_for=(ConnectionError, TimeoutError),
	retry_kwargs={"max_retries": 3, "countdown": 30},
	retry_backoff=True,
	retry_jitter=True,
)
def enviar_mensagem_task(self, numero: str = None, mensagem: str = None, instancia: str = None):
	"""
	Task Celery para envio de mensagens.
	"""
	if not numero or not mensagem:
		logger.warning(
			"Parametros invalidos | numero=%s mensagem=%s instancia=%s",
			numero,
			mensagem,
			instancia,
		)
		return {
			"success": False,
			"error": "Parametros invalidos",
		}

	resultado = enviar_mensagem(numero, mensagem, instancia)

	if resultado.get("success") is True or resultado.get("status") in (200, 201):
		return resultado

	raise Exception(f"Falha no envio: {resultado}")