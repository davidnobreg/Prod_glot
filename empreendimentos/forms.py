import re
from django import forms
from django.core.exceptions import ValidationError
from .models import Empreendimento, Lote


# Doc: https://docs.djangoproject.com/en/5.1/topics/http/file-uploads/

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


## Formulário para cadastro de Empreendimento
class EmpreendimentoForm(forms.ModelForm):
    class Meta:
        model = Empreendimento
        fields = '__all__'  # ['nome', 'telefone', 'tempo_reserva', 'quantidade_parcela', 'cnpj', 'codBanco', 'banco', 'agencia', 'conta', 'favorecido']
        exclude = ('is_ativo',)

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if not nome:
            return nome

        inativo = Empreendimento.objects.filter(nome__iexact=nome, is_ativo=False).first()
        if inativo:
            if not self.instance.pk or inativo.pk != self.instance.pk:
                raise ValidationError(
                    'Já existe um empreendimento com este nome cadastrado, porém inativo. '
                    'Reative-o em vez de criar um novo.'
                )

        qs = Empreendimento.objects.filter(nome__iexact=nome, is_ativo=True)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um empreendimento ativo com este nome.')

        return nome

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')

        if not cnpj:
            return cnpj

        # Remove máscara (somente números)
        cnpj = re.sub(r'\D', '', cnpj)

        # Validação de tamanho
        if len(cnpj) != 14:
            raise ValidationError("CNPJ deve conter exatamente 14 números.")

        # Evita erro de UNIQUE no update
        qs = Empreendimento.objects.filter(cnpj=cnpj)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Este CNPJ já está cadastrado.")

        return cnpj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['banco'].choices = [
                                           ('', 'Selecione o Banco'),
                                       ] + list(self.fields['banco'].choices)

        # campo contrato removido (Opcao B)

        # Classes padrão
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Campos à esquerda e direita
        left_fields = ['nome', 'telefone', 'tempo_reserva', 'quantidade_parcela', 'tipo_correcao', 'desconto']
        right_fields = ['cnpj', 'razaoSocial', 'banco', 'agencia', 'conta', 'observacao']
        endereco_fields = ['cep', 'rua', 'complemento', 'numero', 'bairro', 'cidade', 'estado']
        representante_fields = ['representante_nome', 'representante_cpf', 'representante_rg', 'matricula', 'cidade_foro']

        config = {
            'nome': {'placeholder': 'Nome do Empreendimento'},
            'telefone': {'placeholder': 'Telefone',
                         'class': 'form-control mb-3 mask-phone'},
            'tempo_reserva': {'placeholder': 'Tempo de Reservas'},
            'quantidade_parcela': {'placeholder': 'Quantidade de Parcelas'},
            'cnpj': {'placeholder': 'CNPJ (apenas números).', 'class': 'form-control mb-3 mask-doc', 'maxlength': '18'},
            'banco': {'placeholder': 'banco'},
            'agencia': {'placeholder': 'Agência'},
            'conta': {'placeholder': 'Conta'},
            'razaoSocial': {'placeholder': 'Razão Social'},
            'tipo_correcao': {'placeholder': 'Tipo de Correção'},
            'desconto': {'placeholder': 'Desconto'},
            'observacao': {'placeholder': 'Observação'},
            'cep': {'placeholder': 'Digite o CEP'},
            'rua': {'placeholder': 'Rua ou Avenida'},
            'complemento': {'placeholder': 'Complemento'},
            'numero': {'placeholder': 'Número'},
            'bairro': {'placeholder': 'Bairro'},
            'cidade': {'placeholder': 'Cidade'},
            'representante_nome': {'placeholder': 'Nome do representante'},
            'representante_cpf': {'placeholder': 'CPF do representante'},
            'representante_rg': {'placeholder': 'RG do representante'},
            'matricula': {'placeholder': 'Matrícula do imóvel'},
            'cidade_foro': {'placeholder': 'Cidade do foro (ex: Mauriti - CE)'},
        }

        # 🔽 FORÇAR TEXTAREA APENAS NOS CAMPOS NECESSÁRIOS
        textarea_fields = {
            'reajuste': 4,
            'observacao': 4,
            #'registroCartorio': 4,

        }

        for field_name, rows in textarea_fields.items():
            if field_name in self.fields:
                self.fields[field_name].widget = forms.Textarea(
                    attrs={
                        'class': 'form-control mb-3',
                        'rows': rows,
                        'placeholder': self.fields[field_name].widget.attrs.get('placeholder', ''),
                        'style': 'resize: vertical;',
                    }
                )


        for field, attrs in config.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update(attrs)

        # Atribuir colunas
        for name in left_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'left'
        for name in right_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'right'
        for name in endereco_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'endereco'
        for name in representante_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'representante'

        # Formatação inicial de CNPJ
        if self.instance and self.instance.pk:
            doc = self.instance.cnpj
            if doc:
                if len(doc) == 14:
                    self.initial['cnpj'] = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"



## Formulário para upload de arquivos
class ArquivoForm(forms.Form):
    arquivo = forms.FileField(label="Arquivo", required=True)


class EmpreendimentoEnderecoForm(forms.ModelForm):
    """estado = forms.ChoiceField(choices=choices_estado, initial='PB',
                               widget=forms.Select(attrs={'class': 'form-select mb-3'}))"""

    class Meta:
        model = Empreendimento
        fields = '__all__'  # [ 'cep', 'rua', 'complemento', 'numero', 'bairro', 'cidade', 'estado']
        exclude = ('is_ativo', 'id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].required = False

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control mb-3')

        left_fields = ['rua', 'complemento', 'numero', 'cep']
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


class EmpreendimentoUpdateForm(forms.ModelForm):
    class Meta:
        model = Empreendimento
        fields = '__all__'  # ['nome', 'telefone', 'tempo_reserva', 'quantidade_parcela', 'cnpj', 'codBanco', 'banco', 'agencia', 'conta', 'favorecido']
        exclude = ('is_ativo',)

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')

        if not cnpj:
            return cnpj

        # Remove máscara (somente números)
        cnpj = re.sub(r'\D', '', cnpj)

        # Validação de tamanho
        if len(cnpj) != 14:
            raise ValidationError("CNPJ deve conter exatamente 14 números.")

        # Evita erro de UNIQUE no update
        qs = Empreendimento.objects.filter(cnpj=cnpj)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Este CNPJ já está cadastrado.")

        return cnpj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['banco'].choices = [
                                           ('', 'Selecione o Banco'),
                                       ] + list(self.fields['banco'].choices)

        # campo contrato removido (Opcao B)

        # Classes padrão
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Campos por seção
        left_fields = ['nome', 'telefone', 'tempo_reserva', 'quantidade_parcela', 'tipo_correcao', 'desconto']
        right_fields = ['cnpj', 'razaoSocial', 'banco', 'agencia', 'conta', 'reajuste', 'observacao']
        endereco_fields = ['cep', 'rua', 'complemento', 'numero', 'bairro', 'cidade', 'estado']
        representante_fields = ['representante_nome', 'representante_cpf', 'representante_rg', 'matricula', 'cidade_foro']

        config = {
            'nome': {'placeholder': 'Nome do Empreendimento'},
            'telefone': {'placeholder': 'Telefone',
                         'class': 'form-control mb-3 mask-phone'},
            'tempo_reserva': {'placeholder': 'Tempo de Reservas'},
            'quantidade_parcela': {'placeholder': 'Quantidade de Parcelas'},
            'cnpj': {'placeholder': 'CNPJ (apenas números).', 'class': 'form-control mb-3 mask-doc', 'maxlength': '18'},
            'codBanco': {'placeholder': 'Codigo do Banco'},
            'banco': {'placeholder': 'Nome do Banco'},
            'agencia': {'placeholder': 'Agência'},
            'conta': {'placeholder': 'Conta'},
            'razaoSocial': {'placeholder': 'Razão social'},
            'cep': {'placeholder': 'Digite o CEP'},
            'rua': {'placeholder': 'Rua ou Avenida'},
            'complemento': {'placeholder': 'Complemento'},
            'numero': {'placeholder': 'Número'},
            'bairro': {'placeholder': 'Bairro'},
            'cidade': {'placeholder': 'Cidade'},
            'observacao': {'placeholder': 'Observação'},
            'reajuste': {'placeholder': 'reajuste'},
            'desconto': {'placeholder': 'desconto'},
            'representante_nome': {'placeholder': 'Nome do representante'},
            'representante_cpf': {'placeholder': 'CPF do representante'},
            'representante_rg': {'placeholder': 'RG do representante'},
            'matricula': {'placeholder': 'Matrícula do imóvel'},
            'cidade_foro': {'placeholder': 'Cidade do foro (ex: Mauriti - CE)'},
        }

        # 🔽 FORÇAR TEXTAREA APENAS NOS CAMPOS NECESSÁRIOS
        textarea_fields = {
            'reajuste': 2,
            'observacao': 2,
            # 'registroCartorio': 4,

        }

        for field_name, rows in textarea_fields.items():
            if field_name in self.fields:
                self.fields[field_name].widget = forms.Textarea(
                    attrs={
                        'class': 'form-control mb-3',
                        'rows': rows,
                        'placeholder': self.fields[field_name].widget.attrs.get('placeholder', ''),
                        'style': 'resize: vertical;',
                    }
                )

        for field, attrs in config.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update(attrs)

        # Atribuir colunas
        for name in left_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'left'
        for name in right_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'right'
        for name in endereco_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'endereco'
        for name in representante_fields:
            if name in self.fields:
                self.fields[name].widget.attrs['col'] = 'representante'

        # Formatação inicial de CNPJ
        if self.instance and self.instance.pk:
            doc = self.instance.cnpj
            if doc:
                if len(doc) == 14:
                    self.initial['cnpj'] = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"


## Formulário para cadastro de reserva temporário
class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ('cliente_reserva', 'telefone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica classes gerais e placeholders
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Máscara de telefone
        self.fields['telefone'].widget.attrs.update({
            'class': 'form-control mb-3 mask-phone',
            'placeholder': '(99) 99999-9999'
        })

        # Formata valor existente (edição)
        if self.instance and self.instance.telefone:
            tel = self.instance.telefone
            if len(tel) == 11:
                self.initial['telefone'] = f"({tel[:2]}) {tel[2:7]}-{tel[7:]}"
            elif len(tel) == 10:
                self.initial['telefone'] = f"({tel[:2]}) {tel[2:6]}-{tel[6:]}"


class AtualizarLoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ('valor_metro_quadrado', 'medidas', 'confrontacoes', 'dimenssoes')
        labels = {
            'valor_metro_quadrado': 'Valor metro quadrado',
            'medidas': 'Medidas',
            'confrontacoes': 'Confrontacoes',
            'dimenssoes': 'Marcar dimensoes',
        }
        widgets = {
            'valor_metro_quadrado': forms.TextInput(attrs={
                'class': 'form-control mb-3',
                'placeholder': 'R$ 0,00',
            }),
            'medidas': forms.Textarea(attrs={
                'class': 'form-control mb-3',
                'rows': 6,
                'style': 'resize: vertical;',
            }),
            'confrontacoes': forms.Textarea(attrs={
                'class': 'form-control mb-3',
                'rows': 6,
                'style': 'resize: vertical;',
            }),
            'dimenssoes': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
