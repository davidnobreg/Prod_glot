import requests
import logging

logger = logging.getLogger(__name__)

class EvolutionService:
    def __init__(self, server_url, instance, api_key):
        self.server_url = server_url.rstrip('/')
        self.instance = instance
        self.api_key = api_key
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def enviar_mensagem(self, numero, mensagem, options=None):
        """
        Envia mensagem via Evolution API.
        """
        url = f"{self.server_url}/message/sendText/{self.instance}"
        payload = {
            "number": numero,
            "textMessage": {"text": mensagem}
        }

        if options:
            payload["options"] = options

        try:
            logger.info(f"📤 Enviando mensagem para {numero} via EvolutionService: {payload}")
            response = requests.post(url, json=payload, headers=self.headers, timeout=15)
            response.raise_for_status()
            resp_json = response.json()
            logger.info(f"✅ Mensagem enviada: {resp_json}")
            return {"success": True, "response": resp_json}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao enviar mensagem: {e}")
            return {"success": False, "error": str(e)}
