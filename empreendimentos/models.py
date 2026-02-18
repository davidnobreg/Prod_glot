from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from documentos.models import CadastroDocumento




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
    logo = models.ImageField(verbose_name='Logo',
                             null=True, blank=True)
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, help_text="Informe CNPJ (apenas números).")
    codBanco = models.CharField(max_length=10)
    banco = models.CharField(max_length=100, choices=TypeBancos.choices, blank=True, verbose_name='Banco')
    agencia = models.CharField(max_length=10)
    conta = models.CharField(max_length=15)
    razaoSocial = models.CharField(max_length=100)
    rua = models.CharField(max_length=100, blank=True)
    complemento = models.CharField(max_length=50, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cep = models.CharField(max_length=8, blank=True, validators=[RegexValidator(r'^\d{8}$', 'CEP deve ter 8 números')])
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, choices=choices_estado, default='PB', blank=True)
    reajuste = models.TextField(blank=True, null=True)
    #registroCartorio = models.TextField(blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    contrato = models.ForeignKey(
        CadastroDocumento,
        on_delete=models.CASCADE,
        verbose_name='Contrato padrão',
        blank=True, null=True
    )
    is_ativo = models.BooleanField(default=True)

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
    VENDIDO = 'VENDIDO', 'VENDIDO'


class Lote(models.Model):
    id = models.BigAutoField(primary_key=True)
    lote = models.CharField('Nome do Lote', max_length=50)
    area = models.CharField('ÁREA', max_length=50)
    situacao = models.CharField(max_length=100, choices=TypeLote.choices)
    tempo_reservado = models.TimeField(default=timezone.now)
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

    def save(self, *args, **kwargs):
        self.tempo_reservado = timezone.localtime(timezone.now()) + timedelta(minutes=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return "{}".format(self.lote)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['id']
