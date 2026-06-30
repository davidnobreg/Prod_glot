# empreendimentos/tasks.py

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Lote


logger = logging.getLogger(__name__)


# ==========================================================
# TASK 1 — LIBERAR LOTES TRAVADOS / EXPIRADOS
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.destravar_lotes_expirados",
    queue="empreendimentos",
    routing_key="empreendimentos",
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def destravar_lotes_expirados(self):
    """
    Libera automaticamente todos os lotes que estão em EM_RESERVA
    e já ultrapassaram o tempo limite definido em tempo_reservado.
    """

    logger.info("🔄 [CELERY] Iniciando destravamento de lotes expirados")

    agora = timezone.now()

    with transaction.atomic():
        lotes = (
            Lote.objects
            .select_for_update(skip_locked=True)
            .filter(
                situacao="EM_RESERVA",
                tempo_reservado__lte=agora,
            )
        )

        total = lotes.count()

        logger.info(
            "📦 [CELERY] %s lotes encontrados para destravamento",
            total,
        )

        destravados = 0

        for lote in lotes:
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

            destravados += 1

    logger.info(
        "✅ [CELERY] %s lotes destravados com sucesso",
        destravados,
    )

    return destravados


# ==========================================================
# TASK 2 — ALIAS ANTIGO PARA COMPATIBILIDADE
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.liberar_lotes_travados",
    queue="empreendimentos",
    routing_key="empreendimentos",
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_travados(self):
    """
    Mantém compatibilidade caso o Beat esteja chamando
    empreendimentos.tasks.liberar_lotes_travados.
    """

    logger.info("🔁 [CELERY] Alias liberar_lotes_travados chamado")

    return destravar_lotes_expirados()


# ==========================================================
# TASK 3 — LIBERAR PRÉ-RESERVAS EXPIRADAS
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.liberar_lotes_expirados",
    queue="empreendimentos",
    routing_key="empreendimentos",
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_expirados(self):
    """
    Libera lotes em PRE-RESERVA cuja data_termina_reserva já venceu.
    Mantém compatibilidade caso exista Periodic Task antiga no banco.
    """

    logger.info("🔄 [CELERY] Iniciando liberação de pré-reservas expiradas")

    hoje = timezone.now().date()

    with transaction.atomic():
        lotes = (
            Lote.objects
            .select_for_update(skip_locked=True)
            .filter(
                situacao="PRE-RESERVA",
                data_termina_reserva__lte=hoje,
            )
        )

        total = lotes.count()

        logger.info(
            "📦 [CELERY] %s pré-reservas encontradas para liberação",
            total,
        )

        total_processados = 0

        for lote in lotes:
            lote.situacao = "DISPONIVEL"
            lote.cliente_reserva = ""
            lote.telefone = ""

            lote.save(
                update_fields=[
                    "situacao",
                    "cliente_reserva",
                    "telefone",
                ]
            )

            total_processados += 1

    logger.info(
        "✅ [CELERY] Total de pré-reservas liberadas: %s",
        total_processados,
    )

    return total_processados


# ==========================================================
# TASK 4 — VOLTAR LOTE ESPECÍFICO PARA DISPONÍVEL
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.voltar_lote_para_disponivel",
    queue="empreendimentos",
    routing_key="empreendimentos",
    acks_late=True,
)
def voltar_lote_para_disponivel(self, lote_id):
    """
    Força um lote específico a voltar para DISPONIVEL.
    Útil para ações administrativas manuais.
    """

    logger.info(
        "↩️ [CELERY] Solicitada liberação manual do lote ID=%s",
        lote_id,
    )

    try:
        with transaction.atomic():
            lote = (
                Lote.objects
                .select_for_update()
                .get(id=lote_id)
            )

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
            lote_id,
        )
        return False

    logger.info(
        "✅ [CELERY] Lote ID=%s liberado manualmente",
        lote_id,
    )

    return True


# ==========================================================
# TASK 5 — LIBERAR LOTES EM_RESERVA SEM VENDA ATIVA
# ==========================================================

@shared_task(
    bind=True,
    name="empreendimentos.tasks.liberar_lotes_sem_venda",
    queue="empreendimentos",
    routing_key="empreendimentos",
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_sem_venda(self):
    """
    Libera lotes EM_RESERVA que não possuem venda ativa.
    Roda a cada minuto via Celery Beat.
    """
    logger.info("🔍 [CELERY] Verificando lotes EM_RESERVA sem venda ativa")

    with transaction.atomic():
        lotes = (
            Lote.objects
            .select_for_update(skip_locked=True, of=('self',))
            .filter(situacao="EM_RESERVA")
            .exclude(reg_venda__is_ativo=True)
        )

        total = lotes.count()
        logger.info("📦 [CELERY] %s lotes em EM_RESERVA sem venda ativa encontrados", total)

        liberados = 0

        for lote in lotes:
            logger.info("🔓 [CELERY] Liberando lote %s — sem venda ativa", lote.uuid)
            lote.situacao = "DISPONIVEL"
            lote.tempo_reservado = None
            lote.save(update_fields=["situacao", "tempo_reservado"])
            liberados += 1

    logger.info("✅ [CELERY] %s lotes liberados", liberados)
    return liberados