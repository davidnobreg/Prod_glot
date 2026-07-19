import uuid
from django.conf import settings
from django.db import models

from .empreendimento import Empreendimento
from .representante import RepresentanteLegal
from ._validators import (
    _validate_documento_wizard,
    _upload_documento_empreendimento,
    _upload_documento_representante,
)


class DocumentoEmpreendimento(models.Model):

    CATEGORIA_CHOICES = [
        ('contrato_social', 'Contrato Social'),
        ('matricula_imovel', 'Matrícula do Imóvel'),
        ('alvara', 'Alvará'),
        ('memorial_descritivo', 'Memorial Descritivo'),
        ('planta_loteamento', 'Planta do Loteamento'),
        ('licenca_ambiental', 'Licença Ambiental'),
        ('registro_loteamento', 'Registro do Loteamento'),
        ('procuracao', 'Procuração'),
        ('mapa', 'Mapa do Loteamento'),
        ('tabela', 'Tabela de Preços'),
        ('outro', 'Outro'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    empreendimento = models.ForeignKey(
        Empreendimento, on_delete=models.CASCADE,
        related_name='documentos'
    )
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    nome = models.CharField(max_length=255, blank=True,
        help_text='Deixe em branco para usar o nome da categoria')
    arquivo = models.FileField(
        upload_to=_upload_documento_empreendimento,
        validators=[_validate_documento_wizard],
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        verbose_name = 'Documento do Empreendimento'
        verbose_name_plural = 'Documentos do Empreendimento'
        ordering = ['categoria', 'criado_em']

    def nome_exibicao(self):
        return self.nome or self.get_categoria_display()

    def extensao(self):
        return self.arquivo.name.rsplit('.', 1)[-1].lower() if '.' in self.arquivo.name else ''

    def __str__(self):
        return self.nome_exibicao()


class DocumentoRepresentante(models.Model):

    CATEGORIA_CHOICES = [
        # Documentos do representante
        ('rg_representante', 'RG do Representante'),
        ('rg_novo_representante', 'RG (novo modelo) do Representante'),
        ('cnh_representante', 'CNH do Representante'),
        ('cpf_representante', 'CPF do Representante'),
        ('comprovante_residencia', 'Comprovante de Residência'),
        ('procuracao', 'Procuração'),
        # Documentos do cônjuge
        ('rg_conjuge', 'RG do Cônjuge'),
        ('rg_novo_conjuge', 'RG (novo modelo) do Cônjuge'),
        ('cnh_conjuge', 'CNH do Cônjuge'),
        ('cpf_conjuge', 'CPF do Cônjuge'),
        ('certidao_casamento', 'Certidão de Casamento'),
        ('pacto_antenupcial', 'Pacto Antenupcial'),
        ('outro', 'Outro'),
    ]

    CATEGORIAS_CONJUGE = (
        'rg_conjuge', 'rg_novo_conjuge', 'cnh_conjuge', 'cpf_conjuge',
        'certidao_casamento', 'pacto_antenupcial',
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    representante = models.ForeignKey(
        RepresentanteLegal, on_delete=models.CASCADE,
        related_name='documentos'
    )
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    nome = models.CharField(max_length=255, blank=True)
    arquivo = models.FileField(
        upload_to=_upload_documento_representante,
        validators=[_validate_documento_wizard],
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        verbose_name = 'Documento do Representante'
        verbose_name_plural = 'Documentos do Representante'
        ordering = ['categoria', 'criado_em']

    def nome_exibicao(self):
        return self.nome or self.get_categoria_display()

    def extensao(self):
        return self.arquivo.name.rsplit('.', 1)[-1].lower() if '.' in self.arquivo.name else ''

    def __str__(self):
        return self.nome_exibicao()
