import re
from django.db import models
from django.core import validators
from django.contrib.auth.models import AbstractUser


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