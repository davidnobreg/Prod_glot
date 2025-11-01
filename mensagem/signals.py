from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from empreendimentos.models import Lote
from vendas.models import RegisterVenda
from .tasks import enviar_mensagem_task


# Função utilitária
def formatar_telefone(numero):
    if not numero:
        return None
    numeros = ''.join(filter(str.isdigit, str(numero)))
    if len(numeros) == 11:
        numeros = "55" + numeros
    return numeros

# -------------------------
# SIGNAL PARA LOTES
# -------------------------

@receiver(pre_save, sender=Lote)
def pre_save_lote(sender, instance, **kwargs):
    if instance.pk:
        old_instance = Lote.objects.get(pk=instance.pk)
        instance._old_situacao = old_instance.situacao
    else:
        instance._old_situacao = None

@receiver(post_save, sender=Lote)
def post_save_lote(sender, instance, created, **kwargs):
    situacao_atual = instance.situacao
    situacao_antiga = getattr(instance, "_old_situacao", None)

    if situacao_atual == situacao_antiga:
        return

    # Extrai dados
    cliente = getattr(instance, "cliente_reserva", None)
    user = getattr(instance, "user", None)
    telefone_cliente = formatar_telefone(getattr(instance, "telefone", None))
    telefone_user = formatar_telefone(getattr(instance, "telefone_user", None))
    telefone_empr = formatar_telefone(getattr(getattr(instance.quadra, "empr", None), "telefone", None))


    nome_lote = str(instance.lote)
    nome_quadra = str(instance.quadra)
    nome_empr = str(getattr(instance.quadra, "empr", ""))

    # Exemplo de mensagens
    if situacao_atual == "PRE-RESERVA":
        mensagens = [
            (telefone_cliente,f"Senhor *{cliente}*, foi feita a *PRE-RESERVA* do Lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empr}*."),
            (telefone_user, f"*{user}*, a *PRE-RESERVA* do Lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empr}* foi registrada."),
            (telefone_empr, f"O Lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empr}* foi *PRE-RESERVADO* por *{user}* para o cliente *{cliente}* (☎️ *{telefone_cliente}*).")
        ]
    elif situacao_atual == "DISPONIVEL":
        mensagens = [
            (telefone_user, f"O Lote *{nome_lote}* na Quadra *{nome_quadra}* voltou a estar *DISPONÍVEL*."),
            (telefone_empr, f"O Lote *{nome_lote}* na Quadra *{nome_quadra}* do Loteamento *{nome_empr}* voltou ao status *DISPONÍVEL*.")
        ]
    else:
        return

    for numero, mensagem in mensagens:
        if numero:
            enviar_mensagem_task.delay(numero, mensagem)


# -------------------------
# SIGNAL PARA VENDAS
# -------------------------
@receiver(pre_save, sender=RegisterVenda)
def pre_save_venda(sender, instance, **kwargs):
    if instance.pk:
        old_instance = RegisterVenda.objects.get(pk=instance.pk)
        instance._old_tipo_venda = old_instance.tipo_venda
    else:
        instance._old_tipo_venda = None

@receiver(post_save, sender=RegisterVenda)
def post_save_venda(sender, instance, created, **kwargs):
    tipo_atual = instance.tipo_venda
    tipo_antigo = getattr(instance, "_old_tipo_venda", None)

    if tipo_atual == tipo_antigo:
        return

    cliente = instance.cliente.name
    usuario = instance.user.first_name
    lote = instance.lote.lote

    telefone_cliente = formatar_telefone(getattr(getattr(instance, "cliente", None),"fone", None))
    telefone_user = formatar_telefone(getattr(getattr(instance, "user", None), "contato", None))
    telefone_empr = formatar_telefone(getattr(getattr(getattr(getattr(instance, "lote", None),"quadra", None), "empr", None), "telefone", None))


    print(telefone_cliente,telefone_user,telefone_empr)

    nome_lote = str(instance.lote)
    nome_quadra = str(instance.lote.quadra)
    nome_empreendimento = str(instance.lote.quadra.empr)

    mensagens = []

    if tipo_atual == "RESERVADO":
        mensagens = [
            (telefone_user, f"*{usuario}*, a *RESERVA* do Lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empreendimento}* foi registrada."),
            (telefone_empr, f"O Lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empreendimento}* foi *RESERVADO* por *{usuario}* para o cliente *{cliente}* (☎️ *{telefone_cliente}*).")
        ]

    elif tipo_atual == "VENDIDO":
        mensagens = [
            (telefone_cliente, f"Parabéns *{cliente}*! O lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empreendimento}* foi *VENDIDO* em seu nome."),
            (telefone_user, f"*{usuario}*, a venda do lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empreendimento}* foi concluída."),
            (telefone_empr, f"O Lote *{nome_lote}*, Quadra *{nome_quadra}*, do Loteamento *{nome_empreendimento}* foi vendido por *{usuario}* ao cliente *{cliente}* (☎️ *{telefone_cliente}*).")
        ]

    elif tipo_atual == "CANCELADA":
        mensagens = [
            (telefone_cliente, f"Senhor *{cliente}*, informamos que a negociação do Lote *{nome_lote}*, Quadra *{nome_quadra}*, foi *CANCELADA*."),
        ]

    for numero, mensagem in mensagens:
        if numero:
            enviar_mensagem_task.delay(numero, mensagem)
