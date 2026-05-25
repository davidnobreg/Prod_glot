import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.forms import TextInput
from django.core.exceptions import ValidationError

from .models import Cliente, ClienteConjuge, ClienteEndereco, ClienteTelefone, choices_estado


# ===================================================================
# Funções de validação CPF / CNPJ
# ===================================================================
def validar_cpf(cpf):
    """Validação clássica de CPF"""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10 % 11) % 10
    if dig1 != int(cpf[9]):
        return False

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10 % 11) % 10
    return dig2 == int(cpf[10])


def validar_cnpj(cnpj):
    """Validação clássica de CNPJ"""
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1

    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    dig1 = 11 - soma % 11
    dig1 = dig1 if dig1 < 10 else 0
    if dig1 != int(cnpj[12]):
        return False

    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    dig2 = 11 - soma % 11
    dig2 = dig2 if dig2 < 10 else 0
    return dig2 == int(cnpj[13])


# ===================================================================
# FORM CLIENTE
# ===================================================================
class ClienteForm(forms.ModelForm):
    lote_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    origem = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id')

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email:
            return email

        qs = Cliente.objects.filter(email=email)

        # 🔑 ignora o próprio registro no UPDATE
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")

        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')

        if not cpf:
            return cpf

        qs = Cliente.objects.filter(cpf=cpf)

        # 🔑 ignora o próprio registro no UPDATE
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")

        return cpf

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.required = False
            field.widget.attrs.pop('required', None)
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        # Configuração inicial
        if 'nacionalidade' in self.fields:
            self.fields['nacionalidade'].initial = "Brasileiro"

        # Classes padrão
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        # Campos à esquerda e direita
        left_fields = ['name', 'nome_usual', 'data_ns', 'documento', 'numero_rg', 'orgao_emissor_rg', 'estado_civil', 'observacao']
        right_fields = ['naturalidade', 'nacionalidade', 'profissao', 'renda', 'email']

        # Configurações extras de placeholder, classes e estilos
        config = {
            'name': {'placeholder': 'Nome do Cliente'},
            'nome_usual': {'placeholder': 'Nome do Usual'},
            'data_ns': {'id': 'id_data_ns', 'placeholder': 'Data de Nascimento', 'class': 'form-control mb-3 mask-data'},
            'documento': {'placeholder': 'CPF ou CNPJ', 'class': 'form-control mb-3 mask-doc', 'maxlength': '18'},
            'numero_rg': {'placeholder': 'RG', 'class': 'form-control mb-3 mask-rg'},
            'orgao_emissor_rg': {'placeholder': 'Orgão Emissor'},
            'estado_civil': {'id': 'id_estado_civil', 'class': 'form-select mb-3'},
            'naturalidade': {'placeholder': 'Naturalidade'},
            'nacionalidade': {'placeholder': 'Nacionalidade'},
            'profissao': {'placeholder': 'Profissão'},
            'renda': {'placeholder': 'R$ Renda', 'class': 'form-control mb-3 mask-money', 'inputmode': 'decimal'},
            'email': {'placeholder': 'Email'},
            'observacao': {'placeholder': 'Observação', 'class': 'form-control mb-3', 'style': 'height: 90px;'},
        }
        for field, attrs in config.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update(attrs)

        # Input type data_ns
        if 'data_ns' in self.fields:
            self.fields['data_ns'].widget.input_type = 'text'

        if 'renda' in self.fields:
            self.fields['renda'].widget = TextInput(attrs={
                'class': 'form-control mb-3 mask-money',
                'placeholder': 'R$ Renda',
                'inputmode': 'decimal'
            })

        # Atribuir colunas
        for name in left_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'left'
        for name in right_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'right'

        # Formatação inicial de documento e renda
        if self.instance and self.instance.pk:
            doc = self.instance.documento
            if doc:
                if len(doc) == 11:
                    self.initial['documento'] = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
                else:
                    self.initial['documento'] = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"

            if self.instance.renda is not None:
                try:
                    renda = Decimal(str(self.instance.renda))
                    renda = f"{renda:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    self.initial['renda'] = f"R$ {renda}"
                except:
                    pass

    # ---------------------- Validação Documento ----------------------
    def clean_documento(self):
        documento = re.sub(r'[^0-9]', '', self.cleaned_data.get('documento', ''))
        if len(documento) == 11 and not validar_cpf(documento):
            raise ValidationError("CPF inválido.")
        elif len(documento) == 14 and not validar_cnpj(documento):
            raise ValidationError("CNPJ inválido.")
        elif len(documento) not in (11, 14):
            raise ValidationError("Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")
        return documento

    # ---------------------- Validação Renda -------------------------
    def clean_renda(self):
        renda = self.cleaned_data.get('renda')
        if renda in [None, '']:
            return None
        if isinstance(renda, str):
            renda = renda.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                renda = Decimal(renda)
            except InvalidOperation:
                raise ValidationError("Valor de renda inválido.")
        return renda


# ===================================================================
# FORM CLIENTE UPDATE
# ===================================================================

class ClienteUpdateForm(forms.ModelForm):
    lote_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    origem = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id')

    # ===============================================================
    # DESABILITA validação automática de unique=True do Django
    # ===============================================================
    def validate_unique(self):
        pass

    # ===============================================================
    # EMAIL (unicidade correta no UPDATE)
    # ===============================================================
    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email:
            return email

        email = email.strip().lower()

        qs = Cliente.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Este e-mail já está cadastrado.")

        return email

    # ===============================================================
    # DOCUMENTO (CPF / CNPJ + unicidade)
    # ===============================================================
    def clean_documento(self):
        documento = re.sub(r'[^0-9]', '', self.cleaned_data.get('documento', ''))

        # Validação de formato
        if len(documento) == 11 and not validar_cpf(documento):
            raise ValidationError("CPF inválido.")
        elif len(documento) == 14 and not validar_cnpj(documento):
            raise ValidationError("CNPJ inválido.")
        elif len(documento) not in (11, 14):
            raise ValidationError("Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")

        # 🔑 Validação de unicidade ignorando o próprio registro
        qs = Cliente.objects.filter(documento=documento)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Este CPF/CNPJ já está cadastrado.")

        return documento

    # ===============================================================
    # RENDA
    # ===============================================================
    def clean_renda(self):
        renda = self.cleaned_data.get('renda')

        if renda in [None, '']:
            return None

        if isinstance(renda, str):
            renda = renda.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                renda = Decimal(renda)
            except InvalidOperation:
                raise ValidationError("Valor de renda inválido.")

        return renda

    # ===============================================================
    # INIT
    # ===============================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'nacionalidade' in self.fields:
            self.fields['nacionalidade'].initial = "Brasileiro"

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        left_fields = [
            'name', 'nome_usual', 'data_ns', 'documento', 'numero_rg',
            'orgao_emissor_rg', 'estado_civil', 'observacao'
        ]
        right_fields = [
            'naturalidade', 'nacionalidade',
            'profissao', 'renda', 'email'
        ]

        config = {
            'name': {'placeholder': 'Nome do Cliente'},
            'nome_usual': {'placeholder': 'Nome do Usual'},
            'data_ns': {'placeholder': 'Data de Nascimento', 'class': 'form-control mb-3 mask-data'},
            'documento': {'placeholder': 'CPF ou CNPJ', 'class': 'form-control mb-3 mask-doc'},
            'numero_rg': {'placeholder': 'RG', 'class': 'form-control mb-3 mask-rg'},
            'orgao_emissor_rg': {'placeholder': 'Órgão Emissor'},
            'estado_civil': {'class': 'form-select'},
            'renda': {'placeholder': 'R$ Renda', 'class': 'form-control mb-3 mask-money', 'inputmode': 'decimal'},
            'email': {'placeholder': 'Email'},
            'observacao': {'placeholder': 'Observação', 'style': 'height: 90px;'},
        }

        for field, attrs in config.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update(attrs)

        if 'data_ns' in self.fields:
            self.fields['data_ns'].widget.input_type = 'text'

        if 'renda' in self.fields:
            self.fields['renda'].widget = TextInput(attrs={
                'class': 'form-control mb-3 mask-money',
                'placeholder': 'R$ Renda',
                'inputmode': 'decimal'
            })

        for name in left_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'left'

        for name in right_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'right'

        if self.instance.pk:
            if self.instance.documento:
                doc = self.instance.documento
                self.initial['documento'] = (
                    f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
                    if len(doc) == 11
                    else f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
                )

            if self.instance.renda is not None:
                renda = f"{Decimal(self.instance.renda):,.2f}"
                renda = renda.replace(",", "X").replace(".", ",").replace("X", ".")
                self.initial['renda'] = f"R$ {renda}"



# ===================================================================
# FORM ENDEREÇO
# ===================================================================
class ClienteEnderecoForm(forms.ModelForm):
    estado = forms.ChoiceField(choices=choices_estado, initial='PB',
                               widget=forms.Select(attrs={'class': 'form-select mb-3'}))

    class Meta:
        model = ClienteEndereco
        fields = '__all__'
        exclude = ('is_ativo', 'id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].required = False

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        left_fields = ['cep', 'rua', 'complemento', 'numero']
        right_fields = ['bairro', 'cidade', 'estado']

        config = {
            'cep': {'placeholder': 'Digite o CEP'},
            'rua': {'placeholder': 'Rua ou Avenida'},
            'complemento': {'placeholder': 'Complemento'},
            'numero': {'placeholder': 'Número'},
            'bairro': {'placeholder': 'Bairro'},
            'cidade': {'placeholder': 'Cidade'},
        }
        for name, attrs in config.items():
            if name in self.fields:
                self.fields[name].widget.attrs.update(attrs)

        for name in left_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'left'
        for name in right_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'right'


# ===================================================================
# FORM CÔNJUGE
# ===================================================================
class ClienteConjugeForm(forms.ModelForm):
    class Meta:
        model = ClienteConjuge
        fields = '__all__'
        exclude = ('is_ativo', 'id')

    def clean_documento_conjuge(self):
        documento = re.sub(r'[^0-9]', '', self.cleaned_data.get('documento_conjuge', ''))
        if not documento:
            return ''
        if len(documento) == 11 and not validar_cpf(documento):
            raise ValidationError("CPF do cônjuge inválido.")
        elif len(documento) == 14 and not validar_cnpj(documento):
            raise ValidationError("CNPJ do cônjuge inválido.")
        elif len(documento) not in (11, 14):
            raise ValidationError("Documento do cônjuge deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")
        return documento

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        left_fields = ['nome_conjuge', 'documento_conjuge']
        right_fields = ['numero_rg_conjuge', 'orgao_emissor_rg_conjuge']

        config = {
            'nome_conjuge': {'placeholder': 'Nome do Cônjuge'},
            'documento_conjuge': {'placeholder': 'CPF', 'class': 'form-control mb-3 mask-doc'},
            'numero_rg_conjuge': {'placeholder': 'Nº do RG', 'class': 'form-control mb-3 mask-rg'},
            'orgao_emissor_rg_conjuge': {'placeholder': 'Orgão emissor do RG'},
        }
        for field_name, attrs in config.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update(attrs)

        for field_name in left_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['col'] = 'left'
        for field_name in right_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['col'] = 'right'

        if self.instance and self.instance.pk:
            doc = self.instance.documento_conjuge
            if doc:
                if len(doc) == 11:
                    self.initial['documento_conjuge'] = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
                elif len(doc) == 14:
                    self.initial['documento_conjuge'] = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"


# ===================================================================
# FORM TELEFONE
# ===================================================================
class ClienteTelefoneForm(forms.ModelForm):
    class Meta:
        model = ClienteTelefone
        fields = '__all__'
        exclude = ('is_ativo', 'id_telefone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        self.fields['numero'].widget.attrs.update({
            'placeholder': 'Digite o telefone',
            'class': 'form-control mb-3 mask-phone',
            'id': 'telefoneNumero'
        })
        if 'tipo' in self.fields:
            self.fields['tipo'].widget.attrs.update({'class': 'form-select mb-3'})
        if 'observacao' in self.fields:
            self.fields['observacao'].widget.attrs.update({'placeholder': 'Observação'})

        colunas = {'numero': 'left', 'tipo': 'center', 'observacao': 'right'}
        for field, col in colunas.items():
            if field in self.fields:
                self.fields[field].widget.attrs['col'] = col
