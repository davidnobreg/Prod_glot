import requests
from core.env import get_env


class N8nService:
	"""
	Servico para enviar mensagens ao n8n.
	URL e instancia vem do .env.
	"""

	def __init__(self):
		self.url_webhook = get_env("N8N_WEBHOOK_URL", required=True)
		self.instancia = get_env("N8N_INSTANCIA", default="default")

	def enviar_mensagem(self, numero: str, mensagem: str, instancia: str = None, timeout: int = 10):
		"""
		Envia o payload para o n8n.
		Se instancia nao for passada, usa a do .env.
		"""
		payload = {
			"number": numero,
			"text": mensagem,
			"instancia": instancia or self.instancia,
		}

		try:
			response = requests.post(self.url_webhook, json=payload, timeout=timeout)
			response.raise_for_status()
			return {"status": response.status_code, "body": response.json()}
		except requests.RequestException as e:
			return {"status": "error", "error": str(e)}