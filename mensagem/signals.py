from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from empreendimentos.models import Lote
from .tasks import enviar_mensagem_task

# Função utilitária
def formatar_telefone(numero):
    if not numero:
        return None
    numeros = ''.join(filter(str.isdigit, str(numero)))
    if len(numeros) == 11:
        numeros = "55" + numeros
    return numeros

# Pre-save para armazenar valores antigos
@receiver(pre_save, sender=Lote)
def pre_save_lote(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_situacao = None
        instance._old_cliente_reserva = None
        instance._old_telefone = None
        return

    try:
        old_instance = Lote.objects.get(pk=instance.pk)
        instance._old_situacao = old_instance.situacao
        instance._old_cliente_reserva = old_instance.cliente_reserva
        instance._old_telefone = old_instance.telefone
    except Lote.DoesNotExist:
        instance._old_situacao = None
        instance._old_cliente_reserva = None
        instance._old_telefone = None

# Post-save dispara mensagem via Celery
@receiver(post_save, sender=Lote)
def post_save_lote(sender, instance, created, **kwargs):
    situacao_atual = instance.situacao
    situacao_antiga = getattr(instance, "_old_situacao", None)

    if situacao_atual == situacao_antiga:
        return

    cliente = getattr(instance, "cliente_reserva", None)
    user = getattr(instance, "user", None)
    telefone_cliente = formatar_telefone(getattr(instance, "telefone", None))
    telefone_user = formatar_telefone(getattr(instance, "telefone_user", None))
    telefone_empr = formatar_telefone(getattr(getattr(instance.quadra, "empr", None), "telefone", None))

    nome_lote = str(instance.lote)
    nome_quadra = str(instance.quadra)
    nome_empr = str(getattr(instance.quadra, "empr", ""))

    mensagens = []

    if situacao_atual == "PRE-RESERVA":
        mensagens = [
            (telefone_cliente, f"Senhor {cliente}, foi feita a PRE-RESERVA do Lote {nome_lote}, Quadra {nome_quadra}, do Loteamento {nome_empr}."),
            (telefone_user, f"{user}, a PRE-RESERVA do Lote {nome_lote}, Quadra {nome_quadra}, do Loteamento {nome_empr} foi registrada."),
            (telefone_empr, f"O Lote {nome_lote}, Quadra {nome_quadra}, do Loteamento {nome_empr} foi PRE-RESERVADO por {user} para o cliente {cliente} ({telefone_cliente}).")
        ]
    elif situacao_atual == "DISPONIVEL":
        cliente_antigo = getattr(instance, "_old_cliente_reserva", None)
        telefone_cliente_antiga = formatar_telefone(getattr(instance, "_old_telefone", None))
        mensagens = [
            (telefone_cliente_antiga, f"Senhor {cliente_antigo}, o Cancelamento da RESERVA do Lote {nome_lote}, Quadra {nome_quadra}, do Loteamento {nome_empr} foi realizado com sucesso."),
            (telefone_user, f"O Lote {nome_lote} na Quadra {nome_quadra} voltou a estar DISPONÍVEL."),
            (telefone_empr, f"O Lote {nome_lote} na Quadra {nome_quadra} do Loteamento {nome_empr} voltou ao status DISPONÍVEL.")
        ]
    else:
        return

    # Dispara a task do Celery
    for numero, mensagem in mensagens:
        if numero:
            enviar_mensagem_task.delay(numero, mensagem)
