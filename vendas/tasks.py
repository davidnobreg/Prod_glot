from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Lote, RegisterVenda

@shared_task
def liberar_lotes_reservados_expirados():
    lotes_bloqueados = Lote.objects.filter(situacao="EM_RESERVA")

    for lote in lotes_bloqueados:
        reserva_existente = RegisterVenda.objects.filter(lote=lote).first()

        if not reserva_existente or reserva_existente.dt_reserva < timezone.now():
            lote.situacao = "DISPONIVEL"
            lote.save()
            print(f"Lote {lote.id} liberado automaticamente após expiração.")
