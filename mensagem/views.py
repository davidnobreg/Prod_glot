from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .tasks import enviar_mensagem_task

@csrf_exempt
def enviar_mensagem_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método não permitido"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)

    numero = data.get("numero")
    mensagem = data.get("mensagem")
    options = data.get("options")

    if not numero or not mensagem:
        return JsonResponse({"success": False, "error": "Número e mensagem são obrigatórios"}, status=400)

    # Executa a task de forma assíncrona
    async_result = enviar_mensagem_task.delay(numero, mensagem, options)
    return JsonResponse({"success": True, "task_id": async_result.id})
