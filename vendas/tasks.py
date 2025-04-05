from celery import shared_task
from datetime import datetime, timedelta
from django.db import transaction
from .models import RegisterVenda  # Importando os modelos necessários


@shared_task
def liberar_lotes_reservados_expirados():
    """Libera lotes reservados que já expiraram e não foram vendidos"""

    # Obtém todas as vendas que estão com tipo_venda 'Reservado' e otimiza consultas com select_related
    vendas_reservadas = RegisterVenda.objects.filter(tipo_venda="RESERVADO").select_related("lote__quadra__empr")


    for venda in vendas_reservadas:
        lote = venda.lote  # Obtém o lote da venda
        print(lote)
        prazo_reserva = lote.quadra.empr.tempo_reserva  # Obtém o prazo do empreendimento
        data_limite = venda.dt_reserva + timedelta(days=prazo_reserva)  # Calcula a data limite

        # Se a reserva expirou e o lote não foi vendido, libera o lote e cancela a venda
        if datetime.now().date() > data_limite and lote.situacao == "RESERVADO":
            with transaction.atomic():
                venda.lote.situacao = "DISPONIVEL"  # Atualiza o status do lote para disponível
                venda.tipo_venda = "CANCELADA"  # Cancela a venda
                venda.save()

                print(f"Lote {lote.id} foi liberado e a venda {venda.id} foi cancelada.")

    return "Processo de liberação de lotes concluído!"
