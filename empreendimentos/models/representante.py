import re
import uuid
from django.db import models
from django.db.models import Q

from .empreendimento import Empreendimento
from ._choices import CHOICES_ESTADO_CIVIL


## Representante legal (sócio/administrador) do Empreendimento
class RepresentanteLegal(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    empreendimento = models.ForeignKey(
        Empreendimento, on_delete=models.CASCADE,
        related_name='representantes'
    )
    nome = models.CharField(max_length=255, blank=True)
    documento = models.CharField(max_length=14, blank=True)  # CPF normalizado (somente números)
    numero_rg = models.CharField(max_length=30, blank=True)
    orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    estado_civil = models.CharField(max_length=22, choices=CHOICES_ESTADO_CIVIL, blank=True)
    endereco = models.ForeignKey(
        'base.Endereco', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='representantes'
    )
    is_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Cônjuge — só preenchido se estado_civil = 'casado'
    conj_nome = models.CharField(max_length=255, blank=True)
    conj_documento = models.CharField(max_length=14, blank=True)  # CPF
    conj_numero_rg = models.CharField(max_length=30, blank=True)
    conj_orgao_emissor_rg = models.CharField(max_length=20, blank=True)

    def save(self, *args, **kwargs):
        self.nome = self.nome.strip().upper()
        self.documento = re.sub(r'\D', '', self.documento)
        if self.email:
            self.email = self.email.strip().lower()
        if self.conj_nome:
            self.conj_nome = self.conj_nome.strip().upper()
        if self.conj_documento:
            self.conj_documento = re.sub(r'\D', '', self.conj_documento)
        super().save(*args, **kwargs)

    def __str__(self):
        return "{}".format(self.nome)

    class Meta:
        # unique_together simples bloquearia múltiplos representantes sem CPF
        # no mesmo empreendimento — documento é blank=True (string vazia, não
        # NULL), e '' == '' conta como duplicata pro Postgres. A constraint
        # condicional só vale quando documento está preenchido, permitindo
        # cadastro parcial (CPF opcional) sem abrir mão da unicidade real.
        constraints = [
            models.UniqueConstraint(
                fields=['empreendimento', 'documento'],
                condition=~Q(documento=''),
                name='uniq_representante_empreendimento_documento_preenchido',
                violation_error_message='Já existe um representante com este CPF cadastrado para este empreendimento.',
            ),
        ]
        verbose_name = 'Representante Legal'
        verbose_name_plural = 'Representantes Legais'
