import re
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

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
    name = models.CharField(max_length=100)
    data_ns = models.DateField(blank=True, null=True)
    documento = models.CharField(max_length=18, unique=True, help_text="Informe CPF ou CNPJ (apenas números).")
    numero_rg = models.CharField(max_length=20, blank=True)
    orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=200, unique=True)
    profissao = models.CharField(max_length=100, blank=True)
    estado_civil = models.CharField(max_length=22, choices=choices_estado_civil, default="solteiro")
    renda = models.DecimalField( max_digits=10, decimal_places=2, blank=True, null=True)
    naturalidade = models.CharField(max_length=50, blank=True)
    nacionalidade = models.CharField(max_length=100, default="Brasileiro")
    observacao = models.TextField(blank=True)
    is_ativo = models.BooleanField(default=True)

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
    """def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().upper()
        if self.email:
            self.email = self.email.strip().lower()
        if self.documento:
            self.documento = re.sub(r'\D', '', self.documento)
        if self.renda is not None and isinstance(self.renda, str):
            self.renda = Decimal(self.renda.replace(',', '.'))

        super().save(*args, **kwargs)"""

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().upper()

        if self.email:
            self.email = self.email.strip().lower()

        if self.documento:
            self.documento = re.sub(r'\D', '', self.documento)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']

    def __str__(self):
        return self.name

# ==========================================================
# CÔNJUGE (OneToOne → Cliente)
# ==========================================================
class ClienteConjuge(models.Model):
    cliente = models.OneToOneField(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="conjuge"
    )
    nome_conjuge = models.CharField(max_length=100)
    numero_rg_conjuge = models.CharField(max_length=20, blank=True)
    orgao_emissor_rg_conjuge = models.CharField(max_length=20, blank=True)
    documento_conjuge = models.CharField(
        max_length=14, unique=True, blank=True, null=True,
        help_text="Informe CPF do cônjuge (apenas números)."
    )
    is_ativo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.nome_conjuge:
            self.nome_conjuge = self.nome_conjuge.strip().upper()
        if self.documento_conjuge:
            self.documento_conjuge = re.sub(r'\D', '', self.documento_conjuge)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_conjuge

# ==========================================================
# ENDEREÇO (OneToOne → Cliente)
# ==========================================================
class ClienteEndereco(models.Model):
    id = models.BigAutoField(primary_key=True)
    cliente = models.OneToOneField(
        Cliente, on_delete=models.CASCADE, related_name="endereco", null=True, blank=True
    )
    rua = models.CharField(max_length=100, blank=True)
    complemento = models.CharField(max_length=50, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cep = models.CharField(max_length=8, blank=True, validators=[RegexValidator(r'^\d{8}$', 'CEP deve ter 8 números')])
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, choices=choices_estado, default='PB', blank=True)
    is_ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.rua}, {self.numero} - {self.cidade}/{self.estado}"

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
