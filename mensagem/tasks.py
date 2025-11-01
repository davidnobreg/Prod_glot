from __future__ import absolute_import, unicode_literals
from celery import shared_task
import requests
import os
import logging

logger = logging.getLogger(__name__)
API_MENSAGEM_URL = os.getenv("API_MENSAGEM_URL", "http://prod.carlosecelsoimoveis.com.br/mensagem/enviar/")

@shared_task(bind=True, max_retries=3)
def enviar_mensagem_task(self, numero, mensagem):
    if not numero:
        logger.warning("⚠️ Telefone vazio, tarefa ignorada.")
        return

    payload = {"numero": numero, "mensagem": mensagem}
    logger.info(f"📤 Enviando POST para {API_MENSAGEM_URL}: {payload}")

    try:
        response = requests.post(API_MENSAGEM_URL, json=payload, timeout=15)
        response.raise_for_status()
        resp_json = response.json()
        if resp_json.get("success", False):
            logger.info(f"✅ Mensagem enviada com sucesso para {numero}")
        else:
            logger.error(f"❌ Erro na API: {resp_json}")
            raise self.retry(exc=Exception(f"Falha na API: {resp_json}"), countdown=10)
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Exceção ao enviar para {numero}: {e}")
        raise self.retry(exc=e, countdown=10)
