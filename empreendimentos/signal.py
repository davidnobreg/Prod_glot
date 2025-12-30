# empreendimentos/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from empreendimentos.models import Lote
from mensagem.models import MensagemOutbox


@receiver(post_save, sender=Lote)
def lote_signal(sender, instance, created, **kwargs):

    if not instance.telefone:
        return

    MensagemOutbox.objects.create(
        telefone=instance.telefone,
        mensagem=f"O lote {instance.lote} mudou para {instance.situacao}",
    )
