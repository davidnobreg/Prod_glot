# empreendimentos/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes

from .models import Lote
>>>>>>> Stashed changes

logger = logging.getLogger(__name__)


<<<<<<< Updated upstream
<<<<<<< Updated upstream
@shared_task(
    bind=True,
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
=======
# ==========================================================
# TASK 1 — DESTRAVAR LOTES EXPIRADOS
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.destravar_lotes_expirados",
    queue="app_empreendimentos.lotes",
    routing_key="empreendimentos",
    acks_late=True,
)
def destravar_lotes_expirados(self):
    """
    Libera automaticamente todos os lotes que estão em reserva
    e já ultrapassaram o tempo limite.
    Task idempotente e segura para múltiplos workers.
    """

    logger.info("🔄 [CELERY] Iniciando destravamento de lotes expirados")

    agora = timezone.now()

=======
# ==========================================================
# TASK 1 — DESTRAVAR LOTES EXPIRADOS
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.destravar_lotes_expirados",
    queue="app_empreendimentos.lotes",
    routing_key="empreendimentos",
    acks_late=True,
)
def destravar_lotes_expirados(self):
    """
    Libera automaticamente todos os lotes que estão em reserva
    e já ultrapassaram o tempo limite.
    Task idempotente e segura para múltiplos workers.
    """

    logger.info("🔄 [CELERY] Iniciando destravamento de lotes expirados")

    agora = timezone.now()

>>>>>>> Stashed changes
    lotes = (
        Lote.objects
        .select_for_update(skip_locked=True)
        .filter(
            situacao="EM_RESERVA",
            tempo_reservado__lte=agora
        )
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    )

    total = lotes.count()
    logger.info("📦 [CELERY] %s lotes encontrados para destravamento", total)

    destravados = 0

    for lote in lotes:
        with transaction.atomic():
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            lote.save(update_fields=["situacao", "cliente_reserva", "telefone"])
            liberados += 1
=======
=======
>>>>>>> Stashed changes
            lote.tempo_reservado = None
            lote.save(
                update_fields=[
                    "situacao",
                    "cliente_reserva",
                    "telefone",
                    "tempo_reservado",
                ]
            )
            destravados += 1
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    logger.info(
        "✅ [CELERY] %s lotes destravados com sucesso",
        destravados
    )

    return destravados


<<<<<<< Updated upstream
<<<<<<< Updated upstream
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_expirados(self):
    from .models import Lote  # 👈 IMPORT AQUI
=======
=======
>>>>>>> Stashed changes
# ==========================================================
# TASK 2 — VOLTAR LOTE ESPECÍFICO PARA DISPONÍVEL
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.voltar_lote_para_disponivel",
    queue="app_empreendimentos.lotes",
    routing_key="empreendimentos",
    acks_late=True,
)
def voltar_lote_para_disponivel(self, lote_id):
    """
    Força um lote específico a voltar para DISPONÍVEL.
    Útil para ações administrativas manuais.
    """

    logger.info(
        "↩️ [CELERY] Solicitada liberação manual do lote ID=%s",
        lote_id
    )
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    try:
        with transaction.atomic():
            lote = (
                Lote.objects
                .select_for_update()
                .get(id=lote_id)
            )

<<<<<<< Updated upstream
<<<<<<< Updated upstream
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
=======
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""
            lote.tempo_reservado = None
            lote.save(
                update_fields=[
                    "situacao",
                    "cliente_reserva",
                    "telefone",
                    "tempo_reservado",
                ]
            )

    except Lote.DoesNotExist:
        logger.warning(
            "⚠️ [CELERY] Lote ID=%s não encontrado",
            lote_id
        )
        return False

=======
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""
            lote.tempo_reservado = None
            lote.save(
                update_fields=[
                    "situacao",
                    "cliente_reserva",
                    "telefone",
                    "tempo_reservado",
                ]
            )

    except Lote.DoesNotExist:
        logger.warning(
            "⚠️ [CELERY] Lote ID=%s não encontrado",
            lote_id
        )
        return False

>>>>>>> Stashed changes
    logger.info(
        "✅ [CELERY] Lote ID=%s liberado manualmente",
        lote_id
    )

    return True
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
