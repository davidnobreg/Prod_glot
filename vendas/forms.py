from django import forms
from .models import RegisterVenda
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError


class RegisterVendaForm(forms.ModelForm):
    class Meta:
        model = RegisterVenda
        fields = [
            'cliente',
            'corretor',
            'valor_entrada',
            'valor_sinal',
            #'valor_inicio_contrato',
            'quantidade_parcelas',
            'dt_primeira_parcela',
            'reajuste'
        ]
        exclude = ('is_ativo', 'id')

        labels = {
            'cliente': 'Cliente',
            'valor_entrada': 'Valor da Entrada',
            'valor_sinal': 'Valor do Sinal',
            #'valor_inicio_contrato': 'Valor do Inicio do Contrato',
            'quantidade_parcelas': 'Quantidade de Parcelas',
            'dt_primeira_parcela': 'Data da Primeira Parcela',
            'corretor': 'Corretor',
            'reajuste': 'Correção'
        }

        widgets = {
            'dt_primeira_parcela': forms.DateInput(attrs={
                'type': 'text',
                'class': 'form-control mb-3 datepicker',
            }),
            'cliente': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),
            'corretor': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),
            'reajuste': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),

        }

    def __init__(self, *args, empreendimento=None, venda=None, lote=None, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # -------- Labels vazios personalizados --------
        if 'cliente' in self.fields:
            self.fields['cliente'].empty_label = "Selecione o Cliente"

        # -------- Controle de permissão do campo corretor --------
        """if self.user:
            if self.user.tipo_usuario != 'ADMINISTRADOR' and 'CORRETOR' in self.fields:
                self.fields.pop('CORRETOR')"""

        # -------- Controle de permissão do campo corretor --------
        if not self.user or self.user.tipo_usuario != 'ADMINISTRADOR':
            self.fields.pop('corretor', None)

        if 'corretor' in self.fields:
            self.fields['corretor'].empty_label = "Selecione o Corretor"

        # -------- Configuração adicional dos campos --------
        if 'quantidade_parcelas' in self.fields:
            self.fields['quantidade_parcelas'].widget.attrs.update({
                'class': 'form-control mb-3'
            })

        # -------- Campo reajuste como Select Sim/Não --------
            if 'reajuste' in self.fields:
                self.fields['reajuste'] = forms.TypedChoiceField(
                    label='Correção',
                    choices=(
                        ('True', 'Sim'),
                        ('False', 'Não'),
                    ),
                    coerce=lambda x: x == 'True',
                    initial='True',
                    widget=forms.RadioSelect(attrs={
                        'class': 'radio-inline'
                    })
                )

            # Se estiver criando nova venda
            if not self.instance.pk and empreendimento and 'quantidade_parcelas' in self.fields:
                self.fields['quantidade_parcelas'].initial = empreendimento.quantidade_parcela

            if not self.instance.pk and venda and 'quantidade_parcelas_intercalada' in self.fields:
                self.fields['quantidade_parcelas_intercalada'].initial = venda.quantidade_parcelas_intercalada

            # Se estiver criando nova venda e campo existir
            if not self.instance.pk and lote and 'corretor' in self.fields:
                self.fields['corretor'].initial = lote.user

            # Ajuste classe máscara data
            if 'dt_primeira_parcela' in self.fields:
                existing_class = self.fields['dt_primeira_parcela'].widget.attrs.get('class', '')
                self.fields['dt_primeira_parcela'].widget.attrs.update({
                    'class': existing_class + ' mask-data'
                })

            # -------- Classes padrão --------
            for field in self.fields.values():
                field.widget.attrs.setdefault('class', 'form-control mb-3')

            # -------- Organização visual --------
            left_fields = ['cliente', 'corretor', 'valor_entrada', 'valor_sinal', 'valor_inicio_contrato', ]
            right_fields = ['quantidade_parcelas', 'dt_primeira_parcela', 'quantidade_parcelas_intercalada', 'reajuste']

            for name in left_fields:
                if name in self.fields:
                    self.fields[name].widget.attrs['col'] = 'left'

            for name in right_fields:
                if name in self.fields:
                    self.fields[name].widget.attrs['col'] = 'right'

            # -------- Placeholders e máscaras --------
            if 'valor_entrada' in self.fields:
                self.fields['valor_entrada'].widget.attrs.update({
                    'placeholder': 'R$ Valor da Entrada',
                    'class': 'form-control mb-3 mask-money',
                    'inputmode': 'decimal'
                })

            if 'valor_sinal' in self.fields:
                self.fields['valor_sinal'].widget.attrs.update({
                    'placeholder': 'R$ Valor do Sinal',
                    'class': 'form-control mb-3 mask-money',
                    'inputmode': 'decimal'
                })

            if 'valor_inicio_contrato' in self.fields:
                self.fields['valor_inicio_contrato'].widget.attrs.update({
                    'placeholder': 'R$ Valor Inicio do Contrato',
                    'class': 'form-control mb-3 mask-money',
                    'inputmode': 'decimal'
                })

        def clean(self):
            cleaned_data = super().clean()

            if self.user and self.user.tipo_usuario != 'ADMINISTRADOR':
                cleaned_data['corretor'] = self.user

            return cleaned_data

        # ---------------------- Validação valor_sinal -------------------------
        def clean_valor_sinal(self):
            valor_sinal = self.cleaned_data.get('valor_sinal')

            if not valor_sinal:
                return None

            if isinstance(valor_sinal, str):
                valor_sinal = (
                    valor_sinal
                    .replace("R$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )

                try:
                    valor_sinal = Decimal(valor_sinal)
                except InvalidOperation:
                    raise ValidationError("Valor inválido.")

            return valor_sinal

        # ---------------------- Validação valor_inicio_contrato -------------------------
        def clean_valor_inicio_contrato(self):
            valor_inicio_contrato = self.cleaned_data.get('valor_inicio_contrato')

            if not valor_inicio_contrato:
                return None

            if isinstance(valor_inicio_contrato, str):
                valor_inicio_contrato = (
                    valor_inicio_contrato
                    .replace("R$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )

                try:
                    valor_inicio_contrato = Decimal(valor_inicio_contrato)
                except InvalidOperation:
                    raise ValidationError("Valor inválido.")

            return valor_inicio_contrato
