from celery import shared_task
from datetime import timedelta
from django.db import transaction
from django.utils.timezone import now
import logging

from .models import RegisterVenda

logger = logging.getLogger(__name__)

@shared_task
def liberar_lotes_reservados_expirados():
    breakpoint()  # <- Vai abrir o modo interativo
    """
    Libera lotes com reserva vencida, alterando os campos conforme necessário.
    Adicionado modo DEBUG para entender o motivo de não processar algum item.
    """

    vendas_reservadas = RegisterVenda.objects.filter(tipo_venda="RESERVADO").select_related("lote__quadra__empr")

    total_processados = 0

    for venda in vendas_reservadas:
        #breakpoint()  # <- Vai abrir o modo interativo
        try:
            lote = venda.lote
            prazo_reserva = lote.quadra.empr.tempo_reserva
            dt_reserva = venda.dt_reserva

            if not dt_reserva:
                logger.warning(f"[IGNORADA] Venda {venda.id} sem data de reserva.")
                continue

            data_limite = dt_reserva + timedelta(days=prazo_reserva)
            hoje = now().date()

            logger.debug(f"[DEBUG] Venda {venda.id} | Reserva: {dt_reserva} | Limite: {data_limite} | Hoje: {hoje} | Situação lote: {lote.situacao}")

            if hoje > data_limite and lote.situacao == "RESERVADO":
                with transaction.atomic():
                    lote.situacao = "DISPONIVEL"
                    lote.cliente_reserva = ""
                    lote.telefone = ""
                    lote.save()

                    venda.tipo_venda = "CANCELADA"
                    venda.save()

                    total_processados += 1
                    logger.info(f"[OK] Lote {lote.id} liberado | Venda {venda.id} cancelada.")
            else:
                logger.info(f"[NÃO ALTERADA] Venda {venda.id} ainda no prazo ou lote não está 'RESERVADO'.")

        except Exception as e:
            logger.error(f"[ERRO] Venda {venda.id} - {str(e)}")

    logger.info(f"[FIM] Total de lotes liberados: {total_processados}")
    return f"Processo concluído. Total de lotes liberados: {total_processados}"
