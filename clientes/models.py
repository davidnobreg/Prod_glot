import re
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator


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

    TIPO_CHOICES = [
        ('RG', 'RG'),
        ('CPF', 'CPF'),
        ('CNH', 'CNH'),
        ('COMPROVANTE_ESTADO_CIVIL', 'Comprovante de Estado Civil'),
        ('COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'),
        ('OUTROS', 'Outros'),
        ('CNPJ', 'CNPJ'),
        ('CONTRATO_SOCIAL', 'Contrato Social'),
        ('RG_CPF_ADMINISTRADOR', 'RG / CPF do Administrador'),
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

    cliente = models.ForeignKey(
        'Cliente',
        on_delete=models.CASCADE,
        related_name='arquivos_cliente'
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
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
