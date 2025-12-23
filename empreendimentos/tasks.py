# empreendimentos/tasks.py

from celery import shared_task
import logging
from django.utils import timezone
from django.db import transaction
from .models import Lote

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def liberar_lotes_travados():
    agora = timezone.now()

    logger.info("🔄 [CELERY] Iniciando liberação de lotes travados")

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
            lote.save()
            liberados += 1

    logger.info(f"✅ [CELERY] {liberados} lotes liberados com sucesso")
    return liberados


@shared_task
def liberar_lotes_expirados():
    """
    Atualiza lotes cuja data_termina_reserva já passou.
    Altera apenas o campo 'situacao' do lote para 'DISPONIVEL' se estiver 'PRE-RESERVA'.
    """

    # Filtra apenas os lotes com situação 'PRE-RESERVA'
    lotes_reservados = Lote.objects.filter(situacao="PRE-RESERVA")

    logger.info("🔄 [CELERY] Iniciando liberação de lotes expirados")

    total_processados = 0
    hoje = timezone.now().date()

    for lote in lotes_reservados:
        try:
            if lote.data_termina_reserva and lote.data_termina_reserva <= hoje:
                with transaction.atomic():
                    lote.situacao = "DISPONIVEL"
                    lote.cliente_reserva = ""
                    lote.telefone = ""
                    lote.save()
                    total_processados += 1
                    logger.info(f"[OK] Lote {lote.id} liberado (reserva expirada em {lote.data_termina_reserva}).")
            else:
                logger.debug(f"[IGNORADO] Lote {lote.id} ainda no prazo (termina em {lote.data_termina_reserva}).")
        except Exception as e:
            logger.error(f"[ERRO] Lote {lote.id} - {str(e)}")

    logger.info(f"[FIM] Total de lotes liberados: {total_processados}")
    return f"Processo concluído. Total de lotes liberados: {total_processados}"