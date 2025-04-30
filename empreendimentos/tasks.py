from __future__ import absolute_import, unicode_literals
import logging

from celery import shared_task
from django.utils import timezone
from .models import Lote

# Configuração de logging
logger = logging.getLogger(__name__)

@shared_task
def liberar_lotes_reservados_expirados():
    # Obtém a hora atual
    hora_atual = timezone.now().time()

    # Obtém lotes que estão reservados e cuja hora de reserva é menor que a hora atual
    lotes_expirados = Lote.objects.filter(
        situacao="EM_RESERVA",
        tempo_reservado__lte=hora_atual  # Comparando apenas a hora
    )

    logger.info(f"Verificando {lotes_expirados.count()} lotes expirados.")

    for lote in lotes_expirados:
        lote.situacao = "DISPONIVEL"
        lote.save()
        logger.info(f"Lote {lote.id} alterado para DISPONIVEL após expiração.")


