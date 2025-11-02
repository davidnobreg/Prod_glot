
from django.db import models
from django.contrib.auth.models import AbstractUser
from empreendimentos.models import Empreendimento
from django.core.validators import RegexValidator


class User(AbstractUser):
    choices_tipo_usuario = (('A', 'ADMINISTRADOR'),
                             ('C', 'CORRETOR'),
                             ('P', 'PROPRIETARIO'))

    tipo_usuario = models.CharField(max_length=1, choices=choices_tipo_usuario)
    creci = models.CharField('Creci', max_length=50, blank=True)
    contato = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                message="Telefone deve estar no formato (99) 99999-9999 ou (99) 9999-9999."
            )
        ]
    )

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