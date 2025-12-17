import re
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# ==========================================================
# LISTA DE ESTADOS
# ==========================================================
choices_estado = (
    ('PB', 'Paraíba'), ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PE', 'Pernambuco'),
    ('PI', 'Piauí'), ('PR', 'Paraná'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'),
    ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')
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

    documento = models.CharField(
        max_length=18,
        unique=True,
        help_text="Informe o CPF ou CNPJ do cliente (apenas números)."
    )

    numero_rg = models.CharField(max_length=20, blank=True)
    orgao_emissor_rg = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=200, unique=True)
    profissao = models.CharField(max_length=100, blank=True)
    estado_civil = models.CharField(max_length=22, choices=choices_estado_civil, default="")
    renda = models.CharField(max_length=20, blank=True)
    naturalidade = models.CharField(max_length=50, blank=True)
    nacionalidade = models.CharField(max_length=100, default="Brasileiro")
    observacao = models.CharField(max_length=100, blank=True)
    is_ativo = models.BooleanField(default=True)

    # =====================================================
    # MÉTODO PARA VALIDAR CPF
    # =====================================================
    @staticmethod
    def validar_cpf(cpf):
        cpf = ''.join(filter(str.isdigit, cpf))

        if len(cpf) != 11:
            return False

        if cpf == cpf[0] * 11:
            return False

        def calc(digs):
            s = sum(int(d) * w for d, w in zip(digs, range(len(digs) + 1, 1, -1)))
            resto = 11 - (s % 11)
            return '0' if resto > 9 else str(resto)

        if cpf[-2:] != calc(cpf[:9]) + calc(cpf[:10]):
            return False

        return True

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
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conjuge"
    )

    nome_conjuge = models.CharField(max_length=100)
    numero_rg_conjuge = models.CharField(max_length=20, blank=True)
    orgao_emissor_rg_conjuge = models.CharField(max_length=20, blank=True)

    documento_conjuge = models.CharField(
        max_length=14,
        unique=True,
        help_text="Informe o CPF do cônjuge (somente números).",
        blank = True,
        null = True
    )

    is_ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_conjuge


# ==========================================================
# ENDEREÇO (OneToOne → Cliente)
# ==========================================================
class ClienteEndereco(models.Model):
    idEndereco = models.BigAutoField(primary_key=True)
    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name="endereco",
        null=True,
        blank=True
    )

    rua = models.CharField(max_length=100, blank=True)
    complemento = models.CharField(max_length=50, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cep = models.CharField(max_length=8, blank=True)
    cidade = models.CharField(max_length=100, blank=True)

    estado = models.CharField(
        max_length=2,
        choices=choices_estado,
        default='PB',
        blank=True
    )

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

    id_telefone = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='telefones'
    )

    numero = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
            message="Telefone deve estar no formato (99) 99999-9999."
        )],
        blank=True
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='celular')
    observacao = models.CharField(max_length=100, blank=True)

    is_ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Telefone do Cliente"
        verbose_name_plural = "Telefones dos Clientes"

    def __str__(self):
        return f"{self.numero} ({self.tipo})"
