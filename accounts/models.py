import re
from django.db import models
from django.core import validators
from django.contrib.auth.models import AbstractUser
from empreendimentos.models import Empreendimento


class User(AbstractUser):
    choices_tipo_usuario = (('A', 'ADMINISTRADOR'),
                             ('C', 'CORRETOR'),
                             ('P', 'PROPRIETARIO'))

    tipo_usuario = models.CharField(max_length=1, choices=choices_tipo_usuario)
    creci = models.CharField('Creci', max_length=50, blank=True)
    contato = models.CharField('Contato', max_length=15, blank=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['last_name']

class UsuarioEmpreendimento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    empreendimento = models.ForeignKey(Empreendimento, on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.empreendimento.nome}"