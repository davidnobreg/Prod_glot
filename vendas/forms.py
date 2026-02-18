from django import forms
from .models import RegisterVenda

from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

class RegisterVendaForm(forms.ModelForm):
    class Meta:
        model = RegisterVenda
        fields = ('cliente','valor_sinal', 'dt_primeira_parcela')  # Inclua os campos corretos do modelo
        exclude = ('is_ativo', 'id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        # Classes padrão
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        config = {
            'dt_primeira_parcela': {'id': 'id_data_ns', 'class': 'form-control mb-3 mask-data'},
            'valor_sinal': {'placeholder': 'R$ valor_sinal', 'class': 'form-control mb-3 mask-money', 'inputmode': 'decimal'},
        }

        for field, attrs in config.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update(attrs)

        # Input type data_ns
        if 'dt_primeira_parcela' in self.fields:
            self.fields['dt_primeira_parcela'].widget.input_type = 'text'

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