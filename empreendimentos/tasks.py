# empreendimentos/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="empreendimentos.tasks.liberar_lotes_travados",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_travados(self):
    from .models import Lote  # 👈 IMPORT AQUI

    logger.info("🔄 [CELERY] Iniciando liberação de lotes travados")

    agora = timezone.now()

    lotes = Lote.objects.filter(
        situacao="EM_RESERVA",
        tempo_reservado__lte=agora
    )

    total = lotes.count()
    logger.info(f"📦 [CELERY] {total} lotes encontrados para liberação")

    liberados = 0

    for lote in lotes:
        with transaction.atomic():
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""
            lote.save(update_fields=["situacao", "cliente_reserva", "telefone"])
            liberados += 1

    logger.info(f"✅ [CELERY] {liberados} lotes liberados com sucesso")
    return liberados


@shared_task(
    bind=True,
    name="empreendimentos.tasks.liberar_lotes_expirados",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_expirados(self):
    from .models import Lote  # 👈 IMPORT AQUI

    logger.info("🔄 [CELERY] Iniciando liberação de lotes expirados")

    hoje = timezone.now().date()

    lotes_reservados = Lote.objects.filter(
        situacao="PRE-RESERVA",
        data_termina_reserva__lte=hoje
    )

    total_processados = 0

    for lote in lotes_reservados:
        with transaction.atomic():
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""
            lote.save(update_fields=["situacao", "cliente_reserva", "telefone"])
            total_processados += 1

    logger.info(f"[FIM] Total de lotes liberados: {total_processados}")
    return total_processados
