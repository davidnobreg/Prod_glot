from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User
from rolepermissions.roles import assign_role, clear_roles


@receiver(post_save, sender=User)
def createDefinidorDePermissoes(sender, instance, **kwargs):
    # Limpa as roles anteriores
    clear_roles(instance)

    # Define a nova role com base no tipo de usuário
    if instance.tipo_usuario == "ADMINISTRADOR":
        assign_role(instance, 'administrador')
    elif instance.tipo_usuario == "CORRETOR":
        assign_role(instance, 'corretor')
    elif instance.tipo_usuario == "PROPRIETARIO":
        assign_role(instance, 'proprietario')
