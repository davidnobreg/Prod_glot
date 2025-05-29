from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User
from rolepermissions.roles import assign_role, clear_roles
from django.contrib.auth import get_user_model

@receiver(post_save, sender=User)
def createDefinidorDePermissoes(sender, instance, **kwargs):
    # Limpa as roles anteriores
    clear_roles(instance)

    # Define a nova role com base no tipo de usuário
    if instance.tipo_usuario == "A":
        assign_role(instance, 'administrador')
    elif instance.tipo_usuario == "C":
        assign_role(instance, 'corretor')
    elif instance.tipo_usuario == "P":
        assign_role(instance, 'proprietario')
