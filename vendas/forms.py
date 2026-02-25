from django import forms
from .models import RegisterVenda

from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

class RegisterVendaForm(forms.ModelForm):
    class Meta:
        model = RegisterVenda
        fields = ('cliente','valor_sinal', 'valor_inicio_contrato', 'quantidade_parcelas', 'dt_primeira_parcela', 'corretor')  # Inclua os campos corretos do modelo
        exclude = ('is_ativo', 'id',)
        widgets = {
            'dt_primeira_parcela': forms.DateInput(attrs={'type': 'date'}),
            'corretor': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        # Classes padrão
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        if 'cliente' in self.fields:
            self.fields['cliente'].empty_label = "Selecione o Cliente"

        if 'corretor' in self.fields:
            self.fields['corretor'].empty_label = "Selecione o Corretor"

        config = {
            'cliente': { 'class': 'form-control mb-3'},
            'quantidade_parcelas': {'id': 'id_data_ns', 'class': 'form-control mb-3 mask-data'},
            'dt_primeira_parcela': {'id': 'id_data_ns', 'class': 'form-control mb-3 mask-data'},
            'valor_sinal': {'placeholder': 'R$ valor_sinal', 'class': 'form-control mb-3 mask-money', 'inputmode': 'decimal'},
            'valor_inicio_contrato': {'placeholder': 'R$ valor_sinal', 'class': 'form-control mb-3 mask-money',
                            'inputmode': 'decimal'},
            'corretor': { 'class': 'form-control mb-3'},
        }

        for field, attrs in config.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update(attrs)

        # Input type data_ns
        if 'dt_primeira_parcela' in self.fields:
            self.fields['dt_primeira_parcela'].widget.input_type = 'date'

    # ---------------------- Validação valor_sinal -------------------------
    def clean_valor_sinal(self):
        valor_sinal = self.cleaned_data.get('valor_sinal')
        if valor_sinal in [None, '']:
            return None
        if isinstance(valor_sinal, str):
            valor_sinal = valor_sinal.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                valor_sinal = Decimal(valor_sinal)
            except InvalidOperation:
                raise ValidationError("Valor de renda inválido.")
        return valor_sinal