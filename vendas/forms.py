from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from .models import RegisterVenda


class RegisterVendaForm(forms.ModelForm):
    # =========================================================
    # CORREÇÃO
    # =========================================================

    reajuste = forms.TypedChoiceField(
        label='Correção',
        choices=((True, 'Sim'), (False, 'Não')),
        coerce=lambda v: v == 'True',
        initial=True,
        widget=forms.RadioSelect
    )

    # =========================================================
    # VALOR TOTAL
    # =========================================================

    valor_total = forms.CharField(
        label='Valor Total do Lote',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3 money-readonly',
            'readonly': 'readonly',
        })
    )

    # =========================================================
    # DESCONTO
    # =========================================================

    valor_desconto = forms.CharField(
        label='Desconto',
        required=False,
        initial='R$ 0,00',
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3 mask-money',
            'placeholder': 'R$ 0,00',
            'data-prefix': 'R$ ',
        })
    )

    # =========================================================
    # ENTRADA
    # =========================================================

    valor_entrada = forms.CharField(
        label='Entrada',
        required=False,
        initial='R$ 0,00',
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3 mask-money',
            'placeholder': 'R$ 0,00',
            'data-prefix': 'R$ ',
        })
    )

    # =========================================================
    # SINAL
    # =========================================================

    valor_sinal = forms.CharField(
        label='Sinal',
        required=False,
        initial='R$ 0,00',
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3 mask-money',
            'placeholder': 'R$ 0,00',
            'data-prefix': 'R$ ',
        })
    )

    # =========================================================
    # VALOR PARCELA
    # =========================================================

    valor_parcela = forms.CharField(
        label='Valor da Parcela',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3 money-readonly',
            'readonly': 'readonly',
        })
    )

    class Meta:
        model = RegisterVenda

        fields = [
            'cliente',
            'corretor',

            'valor_total',
            'valor_desconto',

            'valor_entrada',
            'valor_sinal',

            'quantidade_parcelas',
            'valor_parcela',

            'dt_primeira_parcela',
            'reajuste',

            'observacao',
        ]

        widgets = {

            'cliente': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),

            'corretor': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),

            'quantidade_parcelas': forms.NumberInput(attrs={
                'class': 'form-control mb-3',
                'min': 1,
            }),

            'dt_primeira_parcela': forms.DateInput(attrs={
                'class': 'form-control mb-3 datepicker',
                'autocomplete': 'off',
            }),

            'observacao': forms.Textarea(attrs={
                'class': 'form-control mb-3',
                'style': 'height:150px;',
                'placeholder': 'Digite uma observação...',
            }),
        }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self, *args, empreendimento=None, lote=None, user=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.user = user
        self.lote = lote
        self.empreendimento = empreendimento

        self._configure_fields()
        self._set_initial_values()

    # =========================================================
    # CONFIGURAÃƒÆ’Ã¢â‚¬Â¡ÃƒÆ’Ã†â€™O DOS CAMPOS
    # =========================================================

    def _configure_fields(self):

        if not self.user or self.user.tipo_usuario != 'ADMINISTRADOR':

            self.fields.pop('corretor', None)

        else:

            self.fields['corretor'].empty_label = 'Selecione o Corretor'

            if self.lote and not self.instance.pk:
                self.fields['corretor'].initial = self.lote.user

        self.fields['cliente'].empty_label = 'Selecione o Cliente'

        if self.empreendimento and not self.instance.pk:
            self.fields['quantidade_parcelas'].initial = (
                    self.empreendimento.quantidade_parcela or 1
            )

    # =========================================================
    # VALORES INICIAIS
    # =========================================================

    def _set_initial_values(self):

        if not self.lote:
            return

        valor_total = self._calcular_valor_total()

        self.fields['valor_total'].initial = (
            f'R$ {valor_total:,.2f}'
            .replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )

        parcelas = (
                self.fields['quantidade_parcelas'].initial or 1
        )

        valor_parcela = (
                valor_total / Decimal(str(parcelas))
        ).quantize(Decimal('0.01'))

        self.fields['valor_parcela'].initial = (
            f'R$ {valor_parcela:,.2f}'
            .replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )

        # =====================================================
        # DEFAULTS MONEY
        # =====================================================

        self.fields['valor_desconto'].initial = 'R$ 0,00'
        self.fields['valor_entrada'].initial = 'R$ 0,00'
        self.fields['valor_sinal'].initial = 'R$ 0,00'

    # =========================================================
    # MONEY PARSER
    # =========================================================

    def _parse_money(self, value):

        if value in (None, ''):
            return Decimal('0.00')

        if isinstance(value, Decimal):
            return value

        if isinstance(value, str):

            value = (
                value
                .replace('R$', '')
                .replace('.', '')
                .replace(',', '.')
                .strip()
            )

            try:
                return Decimal(value)

            except InvalidOperation:
                raise ValidationError(
                    'Valor monetário inválido.'
                )

        return Decimal(value)

    # =========================================================
    # CLEAN MONEY FIELDS
    # =========================================================

    def clean_valor_entrada(self):
        return self._parse_money(
            self.cleaned_data.get('valor_entrada')
        )

    def clean_valor_sinal(self):
        return self._parse_money(
            self.cleaned_data.get('valor_sinal')
        )

    def clean_valor_parcela(self):
        return self._parse_money(
            self.cleaned_data.get('valor_parcela')
        )

    def clean_valor_desconto(self):

        desconto = self._parse_money(
            self.cleaned_data.get('valor_desconto')
        )

        if self.lote:

            total = self._calcular_valor_total()

            if desconto > total:
                raise ValidationError(
                    'O desconto não pode ser maior que o valor total.'
                )

        return desconto

    # =========================================================
    # CLEAN GLOBAL
    # =========================================================

    def clean(self):

        cleaned = super().clean()

        if self.user and self.user.tipo_usuario != 'ADMINISTRADOR':
            cleaned['corretor'] = self.user

        total = self._calcular_valor_total()

        desconto = self._parse_money(
            cleaned.get('valor_desconto')
        )

        entrada = self._parse_money(
            cleaned.get('valor_entrada')
        )

        sinal = self._parse_money(
            cleaned.get('valor_sinal')
        )

        valor_financiado = (
                total - desconto - entrada - sinal
        )

        if valor_financiado < 0:
            raise ValidationError(
                'O valor financiado não pode ser negativo.'
            )

        return cleaned

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, commit=True):

        instance = super().save(commit=False)

        # ==========================================
        # CORRETOR
        # ==========================================

        if self.user and self.user.tipo_usuario != 'ADMINISTRADOR':
            instance.corretor = self.user

        # ==========================================
        # VALORES
        # ==========================================

        instance.valor_inicio_contrato = (
            self._calcular_valor_total()
        )

        instance.valor_desconto = (
            self._parse_money(
                self.cleaned_data.get(
                    'valor_desconto'
                )
            )
        )

        instance.valor_financiado = (
            self._calcular_valor_financiado()
        )

        instance.valor_parcela = (
            self._calcular_valor_parcela()
        )

        # ==========================================
        # SAVE
        # ==========================================

        if commit:
            instance.save()

        return instance

    # =========================================================
    # CÃƒÆ’Ã‚ÂLCULOS
    # =========================================================

    def _calcular_valor_total(self):

        return (
                Decimal(str(self.lote.area or 0))
                *
                Decimal(str(self.lote.valor_metro_quadrado or 0))
        ).quantize(Decimal('0.01'))

    def _calcular_valor_financiado(self):
        """
        total - desconto - entrada. valor_sinal NÃO entra nessa conta —
        comportamento intencional, confirmado com o cliente (sinal é
        registrado no contrato mas não abate o saldo financiado).
        Não alterar sem validar de novo com o cliente antes.
        """

        total = self._calcular_valor_total()

        desconto = self._parse_money(
            self.cleaned_data.get('valor_desconto')
        )

        entrada = self._parse_money(
            self.cleaned_data.get('valor_entrada')
        )

        sinal = self._parse_money(
            self.cleaned_data.get('valor_sinal')
        )

        return (
                total - desconto - entrada
        ).quantize(Decimal('0.01'))

    def _calcular_valor_parcela(self):

        parcelas = int(
            self.cleaned_data.get('quantidade_parcelas') or 1
        )

        if parcelas <= 0:
            raise ValidationError(
                'Quantidade de parcelas inválida.'
            )

        valor_financiado = (
            self._calcular_valor_financiado()
        )

        return (
                valor_financiado / Decimal(str(parcelas))
        ).quantize(Decimal('0.01'))

