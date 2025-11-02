from django import forms
from django.core.exceptions import ValidationError
from .models import Cliente
import re


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id',)

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '')
        documento = re.sub(r'[^0-9]', '', documento)  # mantém apenas números

        # Validação CPF/CNPJ
        if len(documento) == 11:
            if not Cliente.validar_cpf(documento):
                raise ValidationError("CPF inválido.")
        elif len(documento) == 14:
            if not Cliente.validar_cnpj(documento):
                raise ValidationError("CNPJ inválido.")
        else:
            raise ValidationError("Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")

        return documento  # será salvo no banco sem formatação

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica classes padrão de formatação
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Campos com máscaras específicas
        self.fields['documento'].widget.attrs.update({
            'class': 'form-control mb-3 mask-doc',
            'placeholder': 'Digite o CPF ou CNPJ'
        })
        self.fields['fone'].widget.attrs.update({
            'class': 'form-control mb-3 mask-phone',
            'placeholder': '(99) 99999-9999'
        })

        # Formata automaticamente o valor atual (quando em modo edição)
        if self.instance and self.instance.documento:
            doc = self.instance.documento
            if len(doc) == 11:
                self.initial['documento'] = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
            elif len(doc) == 14:
                self.initial['documento'] = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"


class ClienteModalForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica classes de máscara (para uso em modal ou frontend JS)
        self.fields['documento'].widget.attrs.update({
            'class': 'form-control mask-doc',
            'placeholder': 'CPF ou CNPJ'
        })
        self.fields['fone'].widget.attrs.update({
            'class': 'form-control mask-phone',
            'placeholder': '(99) 99999-9999'
        })
