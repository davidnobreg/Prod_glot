from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User
from rolepermissions.roles import assign_role
from django.contrib.auth import get_user_model

@receiver(post_save, sender=User)
def createDefinidorDePermissoes(sender, instance, **kwargs):

    UserModel = get_user_model()
    try:
        old = UserModel.objects.get(pk=instance.pk)
    except UserModel.DoesNotExist:
        old = None

    if old is None or old.tipo_usuario != instance.tipo_usuario:
        if instance.tipo_usuario == "A":
            assign_role(instance, 'administrador')
        elif instance.tipo_usuario == "C":
            assign_role(instance, 'corretor')
        elif instance.tipo_usuario == "P":
            assign_role(instance, 'proprietario')
