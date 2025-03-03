import re

from django.db import models
from django.core import validators
from django.contrib.auth.models import (AbstractUser, PermissionsMixin, UserManager)


# Create your models here.
class User(AbstractUser, PermissionsMixin):

    class TypeUsuario(models.TextChoices):
        ADMINISTRADOR = 'ADMINISTRADOR', 'ADMINISTRADOR'
        CORRETOR = 'CORRETOR', 'CORRETOR'
        PROPIETARIO = 'PROPIETARIO', 'PROPIETARIO'

    username = models.CharField(
        'Nome do Usuário', max_length=30, unique=True,
            validators=[validators.RegexValidator(re.compile(r'^[\w.@+-]+$'),
                    'O nome do usuario só pode conter letras, digitos ou os '
                    'seguintes caracteres: @/./+/-/_', 'invalid')]
        )
    email = models.EmailField('E-mail', unique=True)
    name = models.CharField('Nome', max_length=100, blank=True)
    creci = models.CharField('Creci', max_length=100, blank=True)
    phone = models.CharField('Telefone', max_length=15, blank=True)
    tipo_usuario = models.CharField(max_length=100, choices=TypeUsuario.choices)
    is_active = models.BooleanField('Está ativo?', blank=True, default=True)
    is_staff = models.BooleanField('É da equipe?', blank=True, default=False)
    date_joined = models.DateTimeField('Data de Entrada', auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.name or self.username

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return str(self)

    class Meta:
        verbose_name= 'Usuário'
        verbose_name_plural = 'Usuarios'
        ordering = ['name']