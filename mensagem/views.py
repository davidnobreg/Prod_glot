from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .services import EvolutionService
from django.conf import settings

# Configurações da sua instância Evolution
SERVER_URL = settings.EVOLUTION_URL
INSTANCE = settings.EVOLUTION_INSTANCE
API_KEY = settings.EVOLUTION_TOKEN

# Cria a instância do service
evolution_service = EvolutionService(SERVER_URL, INSTANCE, API_KEY)

@csrf_exempt
def enviar_mensagem_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)

        numero = data.get("numero")
        mensagem = data.get("mensagem")
        options = data.get("options")  # Opcional

        if not numero or not mensagem:
            return JsonResponse({"success": False, "error": "Número e mensagem são obrigatórios"}, status=400)

        resultado = evolution_service.enviar_mensagem(numero, mensagem, options)
        return JsonResponse(resultado)

    return JsonResponse({"error": "Método não permitido"}, status=405)
