import requests
from django.conf import settings

#server_url = "https://n8n.dnsoftware.com.br/webhook-test/evolution"
instance = settings.EVOLUTION_INSTANCE
api_key = settings.EVOLUTION_TOKEN

numero = "5583999284151"
mensagem = "Teste com payload JSON completo 🚀"

#url = f"{server_url}/message/sendText/{instance}"
url = f"https://n8n.dnsoftware.com.br/webhook-test/evolution"
headers = {
    "apikey": api_key,
    "Content-Type": "application/json",
}

payload = {
    "number": numero,
    "textMessage": {
        "text": mensagem
    }
}

response = requests.post(
    url,
    json=payload,
    headers=headers,
    timeout=15
)

print("Status:", response.status_code)
print("Resposta:", response.text)
