import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class MensagemService:

    @staticmethod
    def enviar(payload: dict):
        required = {"number", "text", "instancia"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Campos obrigatórios ausentes: {missing}")

        url = settings.MENSAGEM_API_URL

        logger.info("📤 Enviando mensagem", extra=payload)

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        response.raise_for_status()

        return response.json()
