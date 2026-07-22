import re
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator

from .validators import validate_documento_representante


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

# ==========================================================
# CLIENTE
# ==========================================================
class Cliente(models.Model):
    choices_estado_civil = (
        ('solteiro', 'Solteiro'),
        ('casado', 'Casado'),
        ('divorciado', 'Divorciado'),
        ('viuvo', 'Viúvo'),
        ('separado_judicialmente', 'Separado judicialmente'),
        ('uniao_estavel', 'União estável')
    )

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )

    name = models.CharField(max_length=100)
    nome_usual = models.CharField(max_length=50, blank=True, null=True)
    data_ns = models.DateField(blank=True, null=True)
    documento = models.CharField(max_length=18, unique=True, help_text="Informe CPF ou CNPJ (apenas números).")
    numero_rg = models.CharField(max_length=20, blank=True)
    orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=200, unique=True)
    profissao = models.CharField(max_length=100, blank=True)
    estado_civil = models.CharField(max_length=22, choices=choices_estado_civil, default="solteiro")
    renda = models.CharField( max_length=20, blank=True, null=True)
    naturalidade = models.CharField(max_length=50, blank=True)
    nacionalidade = models.CharField(max_length=100, default="Brasileiro")
    observacao = models.TextField(blank=True)
    is_ativo = models.BooleanField(default=True)

    # ======================================================
    # ENDEREÇO (desnormalizado de ClienteEndereco)
    # ======================================================
    end_rua = models.CharField(max_length=100, blank=True, null=True)
    end_complemento = models.CharField(max_length=50, blank=True, null=True)
    end_numero = models.CharField(max_length=20, blank=True, null=True)
    end_bairro = models.CharField(max_length=100, blank=True, null=True)
    end_cep = models.CharField(
        max_length=8, blank=True, null=True,
        validators=[RegexValidator(r'^\d{8}$', 'CEP deve ter 8 números')]
    )
    end_cidade = models.CharField(max_length=100, blank=True, null=True)
    end_estado = models.CharField(max_length=2, choices=choices_estado, blank=True, null=True)

    # ======================================================
    # CÔNJUGE (desnormalizado de ClienteConjuge)
    # ======================================================
    conj_nome = models.CharField(max_length=100, blank=True, null=True)
    conj_numero_rg = models.CharField(max_length=20, blank=True, null=True)
    conj_orgao_emissor_rg = models.CharField(max_length=20, blank=True, null=True)
    conj_documento = models.CharField(max_length=14, blank=True, null=True)
    conj_profissao = models.CharField(max_length=100, blank=True, null=True)
    conj_nacionalidade = models.CharField(max_length=100, blank=True, null=True)

    # ======================================================
    # MÉTODO PARA VALIDAR CPF
    # ======================================================
    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False

        def calc(digs):
            s = sum(int(d) * w for d, w in zip(digs, range(len(digs) + 1, 1, -1)))
            resto = 11 - (s % 11)
            return '0' if resto > 9 else str(resto)

        return cpf[-2:] == calc(cpf[:9]) + calc(cpf[:10])

    # ======================================================
    # SALVAR COM AJUSTES AUTOMÁTICOS
    # ======================================================

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().upper()

        if self.email:
            self.email = self.email.strip().lower()

        if self.documento:
            self.documento = re.sub(r"[^0-9]", "", self.documento)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']

    def __str__(self):
        return self.name

# ==========================================================
# DOCUMENTOS DO CLIENTE (tabela auxiliar)
# ==========================================================
class ClienteDocumento(models.Model):

    TIPO_CHOICES_PF = [
        ('RG', 'RG'),
        ('RG_NOVO', 'RG Novo (com CPF)'),
        ('CPF', 'CPF'),
        ('CNH', 'CNH'),
        ('COMPROVANTE_ESTADO_CIVIL', 'Comprovante de Estado Civil'),
        ('COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'),
        ('OUTROS', 'Outros'),
    ]

    TIPO_CHOICES_PJ = [
        ('CNPJ', 'CNPJ'),
        ('CONTRATO_SOCIAL', 'Contrato Social'),
        ('RG_CPF_ADMINISTRADOR', 'RG / CPF do Administrador'),
        ('COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'),
        ('OUTROS', 'Outros'),
    ]

    TIPO_CHOICES_CONJUGE = [
        ('RG_CONJUGE', 'RG do Cônjuge'),
        ('CPF_CONJUGE', 'CPF do Cônjuge'),
        ('CNH_CONJUGE', 'CNH do Cônjuge'),
        ('CERTIDAO_CASAMENTO', 'Certidão de Casamento'),
        ('PACTO_ANTENUPCIAL', 'Pacto Antenupcial'),
    ]

    TIPO_CHOICES = [
        ('RG', 'RG'),
        ('RG_NOVO', 'RG Novo (com CPF)'),
        ('CPF', 'CPF'),
        ('CNH', 'CNH'),
        ('COMPROVANTE_ESTADO_CIVIL', 'Comprovante de Estado Civil'),
        ('COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'),
        ('OUTROS', 'Outros'),
        ('CNPJ', 'CNPJ'),
        ('CONTRATO_SOCIAL', 'Contrato Social'),
        ('RG_CPF_ADMINISTRADOR', 'RG / CPF do Administrador'),
        ('RG_CONJUGE', 'RG do Cônjuge'),
        ('CPF_CONJUGE', 'CPF do Cônjuge'),
        ('CNH_CONJUGE', 'CNH do Cônjuge'),
        ('CERTIDAO_CASAMENTO', 'Certidão de Casamento'),
        ('PACTO_ANTENUPCIAL', 'Pacto Antenupcial'),
    ]

    PERTENCE_A_CHOICES = [
        ('TITULAR', 'Titular'),
        ('CONJUGE', 'Cônjuge'),
    ]

    STATUS_CHOICES = [
        ('processando', 'Processando'),
        ('disponivel', 'Disponível'),
        ('erro', 'Erro'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='disponivel',
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    cliente = models.ForeignKey(
        'Cliente',
        on_delete=models.CASCADE,
        related_name='arquivos_cliente'
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    pertence_a = models.CharField(max_length=10, choices=PERTENCE_A_CHOICES, default='TITULAR')
    arquivo = models.FileField(upload_to='clientes/documentos/')
    descricao = models.CharField(max_length=200, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Documento do Cliente'
        verbose_name_plural = 'Documentos do Cliente'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.cliente}'


# ==========================================================
# TELEFONES (FK → Cliente)
# ==========================================================
class ClienteTelefone(models.Model):
    TIPO_CHOICES = (
        ('celular', 'Celular'),
        ('fixo', 'Fixo'),
        ('recado', 'Recado'),
        ('whatsapp', 'WhatsApp'),
        ('outro', 'Outro'),
    )

    id = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='telefones')
    numero = models.CharField(
        max_length=15, blank=True,
        validators=[RegexValidator(regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                                   message="Telefone deve estar no formato (99) 99999-9999.")]
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='celular')
    observacao = models.CharField(max_length=100, blank=True)
    is_ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.numero} ({self.tipo})"

    class Meta:
        verbose_name = "Telefone do Cliente"
        verbose_name_plural = "Telefones dos Clientes"


# ==========================================================
# REPRESENTANTE LEGAL (sócio/administrador) — cliente PJ
# ==========================================================
class ClienteRepresentante(models.Model):
    """Pessoa física que representa um Cliente PJ (sócio/administrador).

    Não é 1:1 com Cliente (uma PJ pode ter N representantes) e o mesmo CPF
    pode representar mais de uma PJ diferente — por isso `documento` NÃO é
    unique global (ver unique_together), diferente de `Cliente.documento`.
    """

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name='representantes'
    )

    nome = models.CharField(max_length=100)
    documento = models.CharField(max_length=14, help_text="CPF, apenas números.")
    numero_rg = models.CharField(max_length=20, blank=True)
    orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=200, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    estado_civil = models.CharField(
        max_length=22, choices=Cliente.choices_estado_civil, blank=True
    )

    conj_nome = models.CharField(max_length=100, blank=True)
    conj_numero_rg = models.CharField(max_length=20, blank=True)
    conj_orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    conj_documento = models.CharField(max_length=14, blank=True)

    is_ativo = models.BooleanField(default=True)
    endereco = models.ForeignKey(
        'base.Endereco',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='representantes_cliente',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Representante do Cliente'
        verbose_name_plural = 'Representantes do Cliente'
        unique_together = [('cliente', 'documento')]
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome} ({self.documento}) — {self.cliente.name}'

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.strip().upper()
        if self.documento:
            self.documento = re.sub(r"[^0-9]", "", self.documento)
        if self.conj_documento:
            self.conj_documento = re.sub(r"[^0-9]", "", self.conj_documento)
        if self.conj_nome:
            self.conj_nome = self.conj_nome.strip().upper()
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


# ==========================================================
# DOCUMENTOS DO REPRESENTANTE (e do cônjuge dele)
# ==========================================================
class RepresentanteDocumento(models.Model):

    TIPO_CHOICES = [
        # Titular
        ('RG', 'RG'),
        ('CPF', 'CPF'),
        ('CNH', 'CNH'),
        ('PROCURACAO', 'Procuração'),
        ('COMPROVANTE_ESTADO_CIVIL', 'Comprovante de Estado Civil'),
        ('OUTROS', 'Outros'),
        # Cônjuge
        ('RG_CONJUGE', 'RG do Cônjuge'),
        ('CPF_CONJUGE', 'CPF do Cônjuge'),
        ('CNH_CONJUGE', 'CNH do Cônjuge'),
        ('CERTIDAO_CASAMENTO', 'Certidão de Casamento'),
        ('PACTO_ANTENUPCIAL', 'Pacto Antenupcial'),
    ]

    CATEGORIAS_CONJUGE = (
        'RG_CONJUGE', 'CPF_CONJUGE', 'CNH_CONJUGE',
        'CERTIDAO_CASAMENTO', 'PACTO_ANTENUPCIAL',
    )

    PERTENCE_A_CHOICES = [
        ('TITULAR', 'Titular'),
        ('CONJUGE', 'Cônjuge'),
    ]

    STATUS_CHOICES = [
        ('processando', 'Processando'),
        ('disponivel', 'Disponível'),
        ('erro', 'Erro'),
    ]

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    representante = models.ForeignKey(
        ClienteRepresentante, on_delete=models.CASCADE, related_name='documentos'
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    pertence_a = models.CharField(
        max_length=10, choices=PERTENCE_A_CHOICES, default='TITULAR'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='disponivel',
    )
    arquivo = models.FileField(
        upload_to='clientes/documentos_representante/',
        validators=[validate_documento_representante],
    )
    descricao = models.CharField(max_length=200, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Documento do Representante'
        verbose_name_plural = 'Documentos do Representante'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.representante}'
