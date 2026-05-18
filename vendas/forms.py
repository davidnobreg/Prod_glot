from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from .models import RegisterVenda


class RegisterVendaForm(forms.ModelForm):
    """
    Formulário de cadastro de venda/reserva.
    """

    # ==========================================================
    # CAMPOS CUSTOMIZADOS
    # ==========================================================

    tipo_venda_form = forms.ChoiceField(
        label='Tipo de Venda',
        choices=(
            ('avista', 'À Vista'),
            ('parcelado', 'Parcelado'),
        ),
        initial='parcelado',
        widget=forms.RadioSelect
    )

    reajuste = forms.TypedChoiceField(
        label='Correção',
        choices=(
            (True, 'Sim'),
            (False, 'Não'),
        ),
        coerce=lambda value: value == 'True',
        initial=True,
        widget=forms.RadioSelect
    )

    valor_total = forms.DecimalField(
        label='Valor Total',
        required=False,
        disabled=True,
        decimal_places=2,
        max_digits=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3',
            'readonly': 'readonly',
        })
    )

    valor_total_com_desconto = forms.DecimalField(
        label='Valor com Desconto',
        required=False,
        disabled=True,
        decimal_places=2,
        max_digits=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-3',
            'readonly': 'readonly',
        })
    )

    # ==========================================================
    # META
    # ==========================================================

    class Meta:

        model = RegisterVenda

        fields = [
            'cliente',
            'corretor',
            'tipo_venda_form',
            'valor_total',
            'valor_total_com_desconto',
            'valor_entrada',
            'valor_sinal',
            'valor_financiado',
            'quantidade_parcelas',
            'valor_parcela',
            'dt_primeira_parcela',
            'reajuste',
        ]

        labels = {
            'cliente': 'Cliente',
            'corretor': 'Corretor',
            'valor_entrada': 'Valor da Entrada',
            'valor_sinal': 'Valor do Sinal',
            'valor_financiado': 'Valor Financiado',
            'quantidade_parcelas': 'Quantidade de Parcelas',
            'valor_parcela': 'Valor da Parcela',
            'dt_primeira_parcela': 'Data da Primeira Parcela',
        }

        widgets = {

            # ==================================================
            # SELECTS
            # ==================================================

            'cliente': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),

            'corretor': forms.Select(attrs={
                'class': 'form-control mb-3 select2'
            }),

            # ==================================================
            # VALORES
            # ==================================================

            'valor_entrada': forms.TextInput(attrs={
                'class': 'form-control mb-3 mask-money',
                'placeholder': 'R$ 0,00',
                'inputmode': 'decimal',
            }),

            'valor_sinal': forms.TextInput(attrs={
                'class': 'form-control mb-3 mask-money',
                'placeholder': 'R$ 0,00',
                'inputmode': 'decimal',
            }),

            'valor_financiado': forms.TextInput(attrs={
                'class': 'form-control mb-3',
                'readonly': 'readonly',
            }),

            'valor_parcela': forms.TextInput(attrs={
                'class': 'form-control mb-3',
                'readonly': 'readonly',
            }),

            # ==================================================
            # PARCELAS
            # ==================================================

            'quantidade_parcelas': forms.NumberInput(attrs={
                'class': 'form-control mb-3',
                'min': 1,
            }),

            # ==================================================
            # DATA
            # ==================================================

            'dt_primeira_parcela': forms.DateInput(attrs={
                'type': 'text',
                'class': 'form-control mb-3 datepicker mask-data',
            }),
        }

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        *args,
        empreendimento=None,
        lote=None,
        user=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.user = user
        self.lote = lote
        self.empreendimento = empreendimento

        self._configure_cliente()
        self._configure_corretor()
        self._configure_quantidade_parcelas()
        self._configure_valores()
        self._configure_layout()

    # ==========================================================
    # CONFIGURAÇÕES
    # ==========================================================

    def _configure_cliente(self):

        if 'cliente' in self.fields:

            self.fields['cliente'].empty_label = (
                'Selecione o Cliente'
            )

    def _configure_corretor(self):

        if (
            not self.user or
            self.user.tipo_usuario != 'ADMINISTRADOR'
        ):

            self.fields.pop('corretor', None)
            return

        if 'corretor' in self.fields:

            self.fields['corretor'].empty_label = (
                'Selecione o Corretor'
            )

            if (
                not self.instance.pk and
                self.lote
            ):

                self.fields['corretor'].initial = (
                    self.lote.user
                )

    def _configure_quantidade_parcelas(self):

        if (
            not self.instance.pk and
            self.empreendimento and
            'quantidade_parcelas' in self.fields
        ):

            self.fields['quantidade_parcelas'].initial = (
                self.empreendimento.quantidade_parcela
            )

    def _configure_valores(self):

        if not self.lote:
            return

        valor_total = self._calcular_valor_total()

        valor_total_com_desconto = (
            self._calcular_valor_total_com_desconto()
        )

        quantidade_parcelas = Decimal(
            str(
                self.fields[
                    'quantidade_parcelas'
                ].initial or 1
            )
        )

        valor_parcela = (
            valor_total_com_desconto / quantidade_parcelas
        ).quantize(
            Decimal('0.01')
        )

        self.fields['valor_total'].initial = (
            valor_total.quantize(
                Decimal('0.01')
            )
        )

        self.fields[
            'valor_total_com_desconto'
        ].initial = (
            valor_total_com_desconto.quantize(
                Decimal('0.01')
            )
        )

        self.fields['valor_financiado'].initial = (
            valor_total_com_desconto.quantize(
                Decimal('0.01')
            )
        )

        self.fields['valor_parcela'].initial = (
            valor_parcela
        )

    def _configure_layout(self):

        left_fields = [
            'cliente',
            'corretor',
            'tipo_venda_form',
            'valor_entrada',
            'valor_sinal',
        ]

        right_fields = [
            'valor_total',
            'valor_total_com_desconto',
            'valor_financiado',
            'quantidade_parcelas',
            'valor_parcela',
            'dt_primeira_parcela',
            'reajuste',
        ]

        for field_name in left_fields:

            if field_name in self.fields:

                self.fields[
                    field_name
                ].widget.attrs['col'] = 'left'

        for field_name in right_fields:

            if field_name in self.fields:

                self.fields[
                    field_name
                ].widget.attrs['col'] = 'right'

    # ==========================================================
    # CÁLCULOS
    # ==========================================================

    def _calcular_valor_total(self):

        area_lote = Decimal(
            str(self.lote.area or 0)
        )

        valor_metro_quadrado = Decimal(
            str(
                self.lote.valor_metro_quadrado or 0
            )
        )

        return (
            area_lote * valor_metro_quadrado
        )

    def _calcular_valor_total_com_desconto(self):

        valor_total = self._calcular_valor_total()

        desconto = Decimal(
            str(
                self.lote.quadra.empr.desconto or 0
            )
        )

        percentual_desconto = (
            desconto / Decimal('100')
        )

        return (
            valor_total * (
                Decimal('1') - percentual_desconto
            )
        )

    def _calcular_valor_parcela(self):

        valor_total = (
            self._calcular_valor_total_com_desconto()
        )

        tipo_venda = self.data.get(
            'tipo_venda_form'
        ) or self.initial.get(
            'tipo_venda_form',
            'parcelado'
        )

        # ======================================================
        # VENDA À VISTA
        # ======================================================

        if tipo_venda == 'avista':

            return valor_total.quantize(
                Decimal('0.01')
            )

        # ======================================================
        # VENDA PARCELADA
        # ======================================================

        quantidade_parcelas = Decimal(
            str(
                self.data.get(
                    'quantidade_parcelas'
                ) or 1
            )
        )

        return (
            valor_total / quantidade_parcelas
        ).quantize(
            Decimal('0.01')
        )

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _parse_money(value):

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
                    'Informe um valor monetário válido.'
                )

        return Decimal(value)

    # ==========================================================
    # VALIDAÇÕES
    # ==========================================================

    def clean_valor_entrada(self):

        valor_entrada = self.cleaned_data.get(
            'valor_entrada'
        )

        return self._parse_money(
            valor_entrada
        )

    def clean_valor_sinal(self):

        valor_sinal = self.cleaned_data.get(
            'valor_sinal'
        )

        return self._parse_money(
            valor_sinal
        )

    def clean(self):

        cleaned_data = super().clean()

        if (
            self.user and
            self.user.tipo_usuario != 'ADMINISTRADOR'
        ):

            cleaned_data['corretor'] = self.user

        return cleaned_data

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(self, commit=True):

        instance = super().save(commit=False)

        if self.lote:

            instance.valor_financiado = (
                self._calcular_valor_total_com_desconto()
            )

            instance.valor_parcela = (
                self._calcular_valor_parcela()
            )

        if commit:
            instance.save()

        return instance