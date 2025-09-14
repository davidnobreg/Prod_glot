from __future__ import absolute_import, unicode_literals
import logging

from celery import shared_task
from django.utils import timezone
from .models import Lote
from django.db import transaction

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
        lote.cliente_reserva = ""
        lote.telefone = ""
        lote.save()
        logger.info(f"Lote {lote.id} alterado para DISPONIVEL após expiração.")


@shared_task
def liberar_lotes_expirados():
    """
    Atualiza lotes cuja data_termina_reserva já passou.
    Altera apenas o campo 'situacao' do lote para 'DISPONIVEL' se estiver 'PRE-RESERVA'.
    """

    # Filtra apenas os lotes com situação 'PRE-RESERVA'
    lotes_reservados = Lote.objects.filter(situacao="PRE-RESERVA")

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
