import uuid
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


def _validate_logo_arquivo(value):
    ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
    if ext not in ('jpg', 'jpeg'):
        raise ValidationError('Envie JPG ou PNG.')
    if value.size > 10 * 1024 * 1024:
        raise ValidationError('Arquivo não pode exceder 10 MB.')


def _upload_logo_empreendimento(instance, filename):
    return f'empreendimentos/{instance.uuid}/documentos/{filename}'

# ==========================================================
# LISTA DE ESTADOS
# ==========================================================
choices_estado = (
    ('PB', 'Paraíba'), ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'),
    ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'),
    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('PR', 'Paraná'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'),
    ('SE', 'Sergipe'), ('TO', 'Tocantins')
)

class TypeBancos(models.TextChoices):
    BANCOBRASIL = '001', 'Banco do Brasil',
    BANCONORDESTE = '004', 'Banco do Nodeste',
    CAIXAECONOMICA = '104', 'Caixa Economica',
    SICOOB = '756', 'Sicoob',
    SINCRED = '748', 'Sincred',


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



    def __str__(self):
        # return self.nome
        return "{}".format(self.nome)

    class Meta:
        verbose_name = 'Empreendimento'
        verbose_name_plural = 'Empreendimentos'
        ordering = ['id']


## Cadastro de Quadra
class Quadra(models.Model):
    id = models.BigAutoField(primary_key=True)
    namequadra = models.CharField(max_length=50)

    empr = models.ForeignKey(Empreendimento, on_delete=models.CASCADE, related_name='empreendimento')
    def __str__(self):
        return "{}".format(self.namequadra)


## Opções de Imóveis
class TypeLote(models.TextChoices):
    CONSTRUTORA = 'CONSTRUTORA', 'CONSTRUTORA',
    DISPONIVEL = 'DISPONIVEL', 'DISPONIVEL'
    EM_RESERVA = 'EM_RESERVA', 'EM_RESERVA'
    INDISPONIVEL = 'INDISPONIVEL', 'INDISPONIVEL'
    PRE_RESERVA = 'PRE-RESERVA', 'PRE-RESERVA'
    RESERVADO = 'RESERVADO', 'RESERVADO'
    PRE_VENDA = 'PRE-VENDA', 'PRE-VENDA'
    VENDIDO = 'VENDIDO', 'VENDIDO'
    ANALISE = 'ANALISE', 'ANALISE'


class Lote(models.Model):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    lote = models.CharField('Nome do Lote', max_length=50)
    area = models.CharField('ÁREA', max_length=50)
    situacao = models.CharField(max_length=100, choices=TypeLote.choices)
    tempo_reservado = models.DateTimeField(null=True, blank=True)
    quadra = models.ForeignKey(Quadra, on_delete=models.CASCADE, related_name='lotes')
    valor_metro_quadrado = models.CharField('Valor Metro Quadrado', max_length=50, default=00.00)
    cliente_reserva = models.CharField(max_length=100, default=0)
    telefone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                message="Telefone deve estar no formato (99) 99999-9999 ou (99) 9999-9999."
            )
        ]
    )
    user = models.CharField(max_length=100, default=0)
    telefone_user = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                message="Telefone deve estar no formato (99) 99999-9999 ou (99) 9999-9999."
            )
        ]
    )
    data_termina_reserva = models.DateField(default=datetime.now, blank=True)
    largura = models.DecimalField(verbose_name="largura", max_digits=5, decimal_places=2, blank=True, null=True)
    comprimento = models.DecimalField(verbose_name="comprimento", max_digits=5, decimal_places=2, blank=True, null=True)
    dimenssoes = models.BooleanField(default=True)
    confrontacoes = models.TextField(blank=True)
    medidas = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return "{}".format(self.lote)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['id']
