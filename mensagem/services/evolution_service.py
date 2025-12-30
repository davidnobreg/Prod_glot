import requests
import logging
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class EvolutionService:
    def __init__(self, base_url: str, api_key: str, instancia: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instancia = instancia

        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def enviar_mensagem(self, number: str, text: str) -> dict:
        url = f"{self.base_url}/message/sendText/{self.instancia}"

        payload = {
            "number": number,
            "text": text
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=15
            )

            response.raise_for_status()
            return response.json()

        except Timeout:
            logger.error("Timeout ao enviar mensagem")
            raise

        except RequestException as e:
            logger.error(f"Erro HTTP Evolution: {e}")
            raise
