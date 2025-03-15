from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User
from rolepermissions.roles import assign_role

@receiver(post_save, sender=User)
def createDefinidorDePermissoes(sender, instance, created, **kwargs):
    if created:
        if instance.tipo_usuario == "A":
            assign_role(instance, 'administrador')

        elif instance.tipo_usuario == "C":
            assign_role(instance, 'corretor')

        elif instance.tipo_usuario == "P":
            assign_role(instance, 'proprietario')
