# empreendimentos/tasks.py

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Lote

logger = logging.getLogger(__name__)

QUEUE_EMPREENDIMENTOS = "empreendimentos"


def _agora_time():
	return timezone.localtime(timezone.now()).time()


def _liberar_lotes_em_reserva_expirados():
	agora = _agora_time()
	destravados = 0

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
		logger.info("[CELERY] %s lotes EM_RESERVA expirados encontrados", total)

		for lote in lotes:
			lote.situacao = "DISPONIVEL"
			lote.cliente_reserva = ""
			lote.telefone = ""
			lote.save(update_fields=["situacao", "cliente_reserva", "telefone"])
			destravados += 1

	logger.info("[CELERY] %s lotes EM_RESERVA liberados", destravados)
	return destravados


def _liberar_pre_reservas_expiradas():
	hoje = timezone.localdate()
	total_processados = 0

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
		logger.info("[CELERY] %s pre-reservas expiradas encontradas", total)

		for lote in lotes:
			lote.situacao = "DISPONIVEL"
			lote.cliente_reserva = ""
			lote.telefone = ""
			lote.save(update_fields=["situacao", "cliente_reserva", "telefone"])
			total_processados += 1

	logger.info("[CELERY] %s pre-reservas liberadas", total_processados)
	return total_processados


@shared_task(
	bind=True,
	name="empreendimentos.tasks.destravar_lotes_expirados",
	queue=QUEUE_EMPREENDIMENTOS,
	routing_key=QUEUE_EMPREENDIMENTOS,
	acks_late=True,
	autoretry_for=(Exception,),
	retry_kwargs={"max_retries": 3, "countdown": 30},
)
def destravar_lotes_expirados(self):
	return _liberar_lotes_em_reserva_expirados()


@shared_task(
	bind=True,
	name="empreendimentos.tasks.liberar_lotes_travados",
	queue=QUEUE_EMPREENDIMENTOS,
	routing_key=QUEUE_EMPREENDIMENTOS,
	acks_late=True,
	autoretry_for=(Exception,),
	retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_travados(self):
	return _liberar_lotes_em_reserva_expirados()


@shared_task(
	bind=True,
	name="empreendimentos.tasks.liberar_lotes_expirados",
	queue=QUEUE_EMPREENDIMENTOS,
	routing_key=QUEUE_EMPREENDIMENTOS,
	acks_late=True,
	autoretry_for=(Exception,),
	retry_kwargs={"max_retries": 3, "countdown": 30},
)
def liberar_lotes_expirados(self):
	return _liberar_pre_reservas_expiradas()


@shared_task(
	bind=True,
	name="empreendimentos.tasks.voltar_lote_para_disponivel",
	queue=QUEUE_EMPREENDIMENTOS,
	routing_key=QUEUE_EMPREENDIMENTOS,
	acks_late=True,
)
def voltar_lote_para_disponivel(self, lote_id):
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
			lote.save(update_fields=["situacao", "cliente_reserva", "telefone"])

	except Lote.DoesNotExist:
		logger.warning("[CELERY] Lote ID=%s nao encontrado", lote_id)
		return False

	logger.info("[CELERY] Lote ID=%s liberado manualmente", lote_id)
	return True
