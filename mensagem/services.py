import requests

class EvolutionService:
    def __init__(self, server_url, instance, api_key):
        self.server_url = server_url
        self.instance = instance
        self.api_key = api_key
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def enviar_mensagem(self, numero, mensagem, options=None):
        """
        Envia uma mensagem via Evolution API.

        :param numero: número do destinatário no formato 559999999999
        :param mensagem: texto da mensagem
        :param options: dict opcional com delay, mentions, quoted, etc.
        :return: dict com resposta da API
        """
        url = f"{self.server_url}/message/sendText/{self.instance}"
        payload = {
            "number": numero,
            "textMessage": {"text": mensagem}
        }

        if options:
            payload["options"] = options

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()  # Levanta erro para status >= 400
            return {
                "success": True,
                "status": response.status_code,
                "response": response.json()
            }
        except requests.exceptions.HTTPError as errh:
            return {"success": False, "error": f"HTTP Error: {errh}", "status": response.status_code}
        except requests.exceptions.ConnectionError as errc:
            return {"success": False, "error": f"Connection Error: {errc}"}
        except requests.exceptions.Timeout as errt:
            return {"success": False, "error": f"Timeout Error: {errt}"}
        except requests.exceptions.RequestException as err:
            return {"success": False, "error": f"Request Exception: {err}"}
