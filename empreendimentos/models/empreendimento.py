import uuid
from django.db import models
from django.core.validators import RegexValidator

from ._choices import choices_estado, TypeBancos
from ._validators import _validate_logo_arquivo, _upload_logo_empreendimento


## Cadastro de empreendimento
class Empreendimento(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    id = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                message="Telefone deve estar no formato (99) 99999-9999 ou (99) 9999-9999."
            )
        ]
    )
    tempo_reserva = models.IntegerField()
    quantidade_parcela = models.IntegerField()
    logo = models.ImageField(
        upload_to=_upload_logo_empreendimento,
        null=True, blank=True,
        verbose_name='Logo',
    )
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, help_text="Informe CNPJ (apenas números).")
    codBanco = models.CharField(max_length=10, null=True, blank=True)
    banco = models.CharField(max_length=100, choices=TypeBancos.choices, verbose_name='Banco', blank=True)
    agencia = models.CharField(max_length=10, null=True, blank=True)
    conta = models.CharField(max_length=15, null=True, blank=True)
    razaoSocial = models.CharField(max_length=100, null=True, blank=True)
    rua = models.CharField(max_length=100, null=True, blank=True)
    complemento = models.CharField(max_length=50, null=True, blank=True)
    numero = models.CharField(max_length=20, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    cep = models.CharField(max_length=8, null=True, blank=True, validators=[RegexValidator(r'^\d{8}$', 'CEP deve ter 8 números')])
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=2, choices=choices_estado, default='PB', null=True, blank=True)
    #registroCartorio = models.TextField(blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    tipo_correcao = models.CharField(max_length=10, null=True, blank=True, default='IGPM')
    desconto = models.CharField(verbose_name='Desconto', max_length=2, null=True, blank=True, default='0')
    is_ativo = models.BooleanField(default=True)
    representante_nome = models.CharField(max_length=255, blank=True, default='')
    representante_cpf = models.CharField(max_length=20, blank=True, default='')
    representante_rg = models.CharField(max_length=30, blank=True, default='')
    matricula = models.CharField(max_length=100, blank=True, default='')
    cidade_foro = models.CharField(max_length=100, blank=True, default='')
    endereco_empreendimento = models.ForeignKey(
        'base.Endereco', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='empreendimentos'
    )
    endereco_empresa = models.ForeignKey(
        'base.Endereco', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='empresas'
    )



    def __str__(self):
        # return self.nome
        return "{}".format(self.nome)

    class Meta:
        verbose_name = 'Empreendimento'
        verbose_name_plural = 'Empreendimentos'
        ordering = ['id']
