import re
import uuid
from django.conf import settings
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


EXTENSOES_DOCUMENTO_WIZARD = ('pdf', 'jpg', 'jpeg', 'png', 'webp')
TAMANHO_MAXIMO_DOCUMENTO_WIZARD = 20 * 1024 * 1024  # 20MB


def _validate_documento_wizard(value):
    """Extensão + tamanho de documentos anexados no wizard (empreendimento
    e representante) — mesma convenção de `clientes.validators.validate_documento_representante`,
    implementação local pra não criar dependência empreendimentos → clientes."""
    ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
    if ext not in EXTENSOES_DOCUMENTO_WIZARD:
        raise ValidationError('Envie PDF, JPG, PNG ou WEBP.')
    if value.size > TAMANHO_MAXIMO_DOCUMENTO_WIZARD:
        raise ValidationError('Arquivo não pode exceder 20 MB.')


def _upload_documento_empreendimento(instance, filename):
    return f'empreendimentos/documentos/{timezone.now():%Y/%m}/{filename}'


def _upload_documento_representante(instance, filename):
    return f'empreendimentos/representantes/{timezone.now():%Y/%m}/{filename}'

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


CHOICES_ESTADO_CIVIL = (
    ('solteiro', 'Solteiro'),
    ('casado', 'Casado'),
    ('divorciado', 'Divorciado'),
    ('viuvo', 'Viúvo'),
    ('separado_judicialmente', 'Separado judicialmente'),
    ('uniao_estavel', 'União estável'),
)


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
    nome = models.CharField(max_length=255)
    documento = models.CharField(max_length=14)  # CPF normalizado (somente números)
    numero_rg = models.CharField(max_length=30, blank=True)
    orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100)
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
        unique_together = [('empreendimento', 'documento')]
        verbose_name = 'Representante Legal'
        verbose_name_plural = 'Representantes Legais'


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
        ('cpf_representante', 'CPF do Representante'),
        ('comprovante_residencia', 'Comprovante de Residência'),
        ('procuracao', 'Procuração'),
        # Documentos do cônjuge
        ('rg_conjuge', 'RG do Cônjuge'),
        ('cpf_conjuge', 'CPF do Cônjuge'),
        ('certidao_casamento', 'Certidão de Casamento'),
        ('pacto_antenupcial', 'Pacto Antenupcial'),
        ('outro', 'Outro'),
    ]

    CATEGORIAS_CONJUGE = ('rg_conjuge', 'cpf_conjuge', 'certidao_casamento', 'pacto_antenupcial')

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
