from django.db import models


## Cadastro de Clientes
class Cliente(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    documento = models.CharField(max_length=18, default=00000000000) #example default.2
    email = models.EmailField(max_length=200, unique=True)
    fone = models.CharField(max_length=15)
    is_ativo = models.BooleanField(default=False)

    """
    def clean(self):
        documento = self.documento.replace('.', '').replace('-', '').replace('/', '')
        if len(documento) == 11:
            # Validar CPF
            if not self.validar_cpf(documento):
                raise ValidationError({'documento': 'CPF inválido'})
        elif len(documento) == 14:
            # Validar CNPJ
            if not self.validar_cnpj(documento):
                raise ValidationError({'documento': 'CNPJ inválido'})
        else:
            raise ValidationError({'documento': 'Documento inválido'})

    def validar_cpf(self, cpf):
        #Valida um número de CPF.

        # Remove caracteres não numéricos
        cpf = ''.join(filter(str.isdigit, cpf))

        # Verifica se o CPF tem 11 dígitos
        if len(cpf) != 11:
            return False

        # Verifica se todos os dígitos são iguais (CPF inválido)
        if cpf == cpf[0] * 11:
            return False

        # Cálculo do primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf[i]) * (10 - i)
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        # Cálculo do segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf[i]) * (11 - i)
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        # Verifica se os dígitos verificadores calculados coincidem com os do CPF
        if int(cpf[9]) == digito1 and int(cpf[10]) == digito2:
            return True
        else:
            return False
        ...

    def validar_cnpj(self, cnpj):
        #Valida um número de CNPJ.
        cnpj = ''.join(filter(str.isdigit, cnpj))

        if len(cnpj) != 14:
            return False

        if cnpj == cnpj[0] * 14:
            return False

        # Calcula o primeiro dígito verificador
        soma = 0
        for i, digito in enumerate(cnpj[:12]):
            soma += int(digito) * (5 - i % 4)
        resto = soma % 11
        dv1 = 0 if resto < 2 else 11 - resto

        # Calcula o segundo dígito verificador
        soma = 0
        for i, digito in enumerate(cnpj[:13]):
            soma += int(digito) * (6 - i % 4)
        resto = soma % 11
        dv2 = 0 if resto < 2 else 11 - resto

        return cnpj[-2:] == str(dv1) + str(dv2)"""

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']
