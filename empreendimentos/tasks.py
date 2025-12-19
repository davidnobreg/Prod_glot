from celery import shared_task
import logging
from django.utils import timezone
from django.db import transaction
from .models import Lote

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="empreendimentos.tasks.liberar_lotes_travados",
    priority=9,
)
def liberar_lotes_travados(self):
    hora_atual = timezone.now().time()

    lotes = Lote.objects.filter(
        situacao="EM_RESERVA",
        tempo_reservado__lte=hora_atual
    )

    logger.info(f"[CRITICAL] {lotes.count()} lotes a liberar")

    for lote in lotes:
        with transaction.atomic():
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""
            lote.save()
