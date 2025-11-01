import re
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class Cliente(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    documento = models.CharField(
        max_length=18,
        unique=True,
        help_text="Informe o CPF ou CNPJ do cliente (apenas números)."
    )
    email = models.EmailField(max_length=200, unique=True)
    fone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
                message="Telefone deve estar no formato (99) 99999-9999 ou (99) 9999-9999."
            )
        ]
    )
    is_ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']

    def __str__(self):
        return self.name

    # ---------- Validações de documento ----------
    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        cpf = re.sub(r'[^0-9]', '', cpf)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False

        for i in range(9, 11):
            soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
            digito = ((soma * 10) % 11) % 10
            if int(cpf[i]) != digito:
                return False
        return True

    @staticmethod
    def validar_cnpj(cnpj: str) -> bool:
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False

        def calc_dv(cnpj, peso):
            soma = sum(int(n) * p for n, p in zip(cnpj, peso))
            resto = soma % 11
            return '0' if resto < 2 else str(11 - resto)

        peso1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        peso2 = [6] + peso1
        dv1 = calc_dv(cnpj[:12], peso1)
        dv2 = calc_dv(cnpj[:12] + dv1, peso2)
        return cnpj[-2:] == dv1 + dv2

    @classmethod
    def validar_documento(cls, documento: str) -> bool:
        documento = re.sub(r'[^0-9]', '', documento)
        if len(documento) == 11:
            return cls.validar_cpf(documento)
        elif len(documento) == 14:
            return cls.validar_cnpj(documento)
        else:
            return False

    # ---------- Validação ao salvar ----------
    def clean(self):
        documento_limpo = re.sub(r'[^0-9]', '', self.documento)
        if not Cliente.validar_documento(documento_limpo):
            raise ValidationError({'documento': 'CPF ou CNPJ inválido.'})

    def save(self, *args, **kwargs):
        # chama a validação antes de salvar
        self.full_clean()
        super().save(*args, **kwargs)
