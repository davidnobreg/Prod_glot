from django.utils.timezone import now
import logging

logger = logging.getLogger(__name__)

def minha_tarefa():
    logger.info(f"Tarefa executada em: {now()}")