import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from .models import Cliente, ClienteTelefone, choices_estado, _validate_doc_arquivo


# ===================================================================
# Tailwind component class helpers
# ===================================================================
_DROP_WIDGET_CLASSES = {"form-control", "form-select", "mb-3"}

_FILE_FIELDS = (
	'foto_rg_frente', 'foto_rg_verso', 'foto_cpf', 'comprovante_residencia',
	'conj_rg_frente', 'conj_rg_verso', 'certidao_estado_civil',
)


def _merge_classes(existing, *adds):
	parts = []
	for token in (existing or "").split():
		if token and token not in _DROP_WIDGET_CLASSES and token not in parts:
			parts.append(token)
	for add in adds:
		for token in (add or "").split():
			if token and token not in parts:
				parts.append(token)
	return " ".join(parts).strip()


def _apply_widget_style(field):
	widget = field.widget
	if isinstance(widget, forms.HiddenInput):
		return
	if isinstance(widget, forms.Textarea):
		base = "glot-textarea"
	elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
		base = "glot-select"
	else:
		base = "glot-input"
	widget.attrs["class"] = _merge_classes(widget.attrs.get("class"), base)


# ===================================================================
# Validações CPF / CNPJ
# ===================================================================
def validar_cpf(cpf):
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
# FORM BASE CLIENTE
# ===================================================================
class ClienteBaseForm(forms.ModelForm):

	lote_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
	origem = forms.CharField(required=False, widget=forms.HiddenInput())

	class Meta:
		model = Cliente
		fields = '__all__'
		exclude = (
			'is_ativo', 'id',
			'end_rua', 'end_complemento', 'end_numero', 'end_bairro',
			'end_cep', 'end_cidade', 'end_estado',
			'conj_nome', 'conj_numero_rg', 'conj_orgao_emissor_rg', 'conj_documento',
		)
		labels = {
			'name': 'Nome',
			'nome_usual': 'Nome Usual',
			'data_ns': 'Data de Nascimento',
			'documento': 'CPF / CNPJ',
			'numero_rg': 'RG',
			'orgao_emissor_rg': 'Órgão Emissor',
			'estado_civil': 'Estado Civil',
			'naturalidade': 'Naturalidade',
			'nacionalidade': 'Nacionalidade',
			'profissao': 'Profissão',
			'renda': 'Renda',
			'email': 'E-mail',
			'observacao': 'Observação',
		}
		widgets = {
			'name': forms.TextInput(attrs={'class': 'form-control mb-3'}),
			'nome_usual': forms.TextInput(attrs={'class': 'form-control mb-3'}),
			'data_ns': forms.TextInput(attrs={'class': 'form-control mb-3 mask-data'}),
			'documento': forms.TextInput(attrs={'class': 'form-control mb-3 mask-doc', 'maxlength': '18'}),
			'numero_rg': forms.TextInput(attrs={'class': 'form-control mb-3 mask-rg'}),
			'orgao_emissor_rg': forms.TextInput(attrs={'class': 'form-control mb-3'}),
			'estado_civil': forms.Select(attrs={'class': 'form-select mb-3'}),
			'naturalidade': forms.TextInput(attrs={'class': 'form-control mb-3'}),
			'nacionalidade': forms.TextInput(attrs={'class': 'form-control mb-3'}),
			'profissao': forms.TextInput(attrs={'class': 'form-control mb-3'}),
			'renda': forms.TextInput(attrs={
				'class': 'form-control mb-3 mask-money',
				'placeholder': 'R$ 0,00',
				'inputmode': 'decimal',
			}),
			'email': forms.EmailInput(attrs={'class': 'form-control mb-3'}),
			'observacao': forms.Textarea(attrs={'class': 'form-control mb-3', 'style': 'height: 90px;'}),
			# FileInput simples — sem "Currently/Clear" do ClearableFileInput
			'foto_rg_frente': forms.FileInput(),
			'foto_rg_verso': forms.FileInput(),
			'foto_cpf': forms.FileInput(),
			'comprovante_residencia': forms.FileInput(),
			'conj_rg_frente': forms.FileInput(),
			'conj_rg_verso': forms.FileInput(),
			'certidao_estado_civil': forms.FileInput(),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._configure_fields()
		self._set_column_layout()
		self._set_initial_values()

	def _configure_fields(self):
		for name, field in self.fields.items():
			field.required = False
			field.widget.attrs.pop('required', None)
			_apply_widget_style(field)
			if name in _FILE_FIELDS:
				field.widget.attrs['accept'] = '.jpg,.jpeg,.png,.pdf'

		if 'nacionalidade' in self.fields:
			self.fields['nacionalidade'].initial = 'Brasileiro'

		if 'data_ns' in self.fields:
			self.fields['data_ns'].widget.input_type = 'text'
			self.fields['data_ns'].input_formats = ['%d/%m/%Y', '%Y-%m-%d']

	def _set_column_layout(self):
		left_fields = [
			'name', 'nome_usual', 'data_ns', 'documento',
			'numero_rg', 'orgao_emissor_rg', 'estado_civil',
		]
		right_fields = [
			'naturalidade', 'nacionalidade', 'profissao', 'renda', 'email', 'observacao',
		]
		for name in left_fields:
			if name in self.fields:
				self.fields[name].widget.attrs['col'] = 'left'
		for name in right_fields:
			if name in self.fields:
				self.fields[name].widget.attrs['col'] = 'right'

	def _set_initial_values(self):
		if not (self.instance and self.instance.pk):
			return
		doc = self.instance.documento
		if doc:
			if len(doc) == 11:
				self.initial['documento'] = f'{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}'
			else:
				self.initial['documento'] = f'{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}'
		if self.instance.renda is not None:
			try:
				renda = Decimal(str(self.instance.renda))
				renda = f'{renda:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
				self.initial['renda'] = f'R$ {renda}'
			except (InvalidOperation, ValueError):
				pass

	def _parse_money(self, value):
		if value in (None, ''):
			return None
		if isinstance(value, Decimal):
			return value
		if isinstance(value, str):
			value = value.replace('R$', '').replace('.', '').replace(',', '.').strip()
			try:
				return Decimal(value)
			except InvalidOperation:
				raise ValidationError('Valor de renda inválido.')
		return Decimal(value)

	def clean_email(self):
		email = self.cleaned_data.get('email')
		if not email:
			return email
		email = email.strip().lower()
		qs = Cliente.objects.filter(email__iexact=email)
		if self.instance and self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise forms.ValidationError('Este e-mail já está cadastrado.')
		return email

	def clean_documento(self):
		documento = re.sub(r'[^0-9]', '', self.cleaned_data.get('documento', ''))
		if len(documento) == 11 and not validar_cpf(documento):
			raise ValidationError('CPF inválido.')
		elif len(documento) == 14 and not validar_cnpj(documento):
			raise ValidationError('CNPJ inválido.')
		elif len(documento) not in (11, 14):
			raise ValidationError('Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).')
		qs = Cliente.objects.filter(documento=documento)
		if self.instance and self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise ValidationError('Este CPF/CNPJ já está cadastrado.')
		return documento

	def clean_renda(self):
		return self._parse_money(self.cleaned_data.get('renda'))


# ===================================================================
# FORM CLIENTE (criação)
# ===================================================================
class ClienteForm(ClienteBaseForm):
	"""Formulário de criação: nome, documento e e-mail são obrigatórios."""

	def _configure_fields(self):
		super()._configure_fields()
		for name in ('name', 'documento', 'email'):
			if name in self.fields:
				self.fields[name].required = True


# ===================================================================
# FORM CLIENTE UPDATE (edição)
# ===================================================================
class ClienteUpdateForm(ClienteBaseForm):
	"""Formulário de edição: validate_unique desativado (clean_* fazem a checagem)."""

	def validate_unique(self):
		pass


# ===================================================================
# FORM ENDEREÇO — backed por Cliente, campos end_*
# ===================================================================
class ClienteEnderecoForm(forms.ModelForm):

	class Meta:
		model = Cliente
		fields = [
			'end_rua', 'end_complemento', 'end_numero',
			'end_bairro', 'end_cep', 'end_cidade', 'end_estado',
		]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		for field in self.fields.values():
			field.required = False
			_apply_widget_style(field)

		if 'end_estado' in self.fields:
			self.fields['end_estado'].widget = forms.Select(
				choices=[('', '---------')] + list(choices_estado),
				attrs={'class': _merge_classes('form-select', 'glot-select')},
			)

		config = {
			'end_cep': {'placeholder': 'Digite o CEP'},
			'end_rua': {'placeholder': 'Rua ou Avenida'},
			'end_complemento': {'placeholder': 'Complemento'},
			'end_numero': {'placeholder': 'Número'},
			'end_bairro': {'placeholder': 'Bairro'},
			'end_cidade': {'placeholder': 'Cidade'},
		}
		for name, attrs in config.items():
			if name in self.fields:
				self.fields[name].widget.attrs.update(attrs)

		left_fields = ['end_cep', 'end_rua', 'end_complemento', 'end_numero']
		right_fields = ['end_bairro', 'end_cidade', 'end_estado']

		for name in left_fields:
			if name in self.fields:
				self.fields[name].widget.attrs['col'] = 'left'
		for name in right_fields:
			if name in self.fields:
				self.fields[name].widget.attrs['col'] = 'right'


# ===================================================================
# FORM CÔNJUGE — backed por Cliente, campos conj_*
# ===================================================================
class ClienteConjugeForm(forms.ModelForm):

	class Meta:
		model = Cliente
		fields = [
			'conj_nome', 'conj_numero_rg',
			'conj_orgao_emissor_rg', 'conj_documento',
		]

	def clean_conj_documento(self):
		documento = re.sub(r'[^0-9]', '', self.cleaned_data.get('conj_documento', '') or '')
		if not documento:
			return None
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
			field.required = False
			_apply_widget_style(field)

		config = {
			'conj_nome': {'placeholder': 'Nome do Cônjuge'},
			'conj_documento': {'placeholder': 'CPF', 'class': 'mask-doc'},
			'conj_numero_rg': {'placeholder': 'Nº do RG', 'class': 'mask-rg'},
			'conj_orgao_emissor_rg': {'placeholder': 'Órgão emissor do RG'},
		}
		for field_name, attrs in config.items():
			if field_name in self.fields:
				self.fields[field_name].widget.attrs.update(attrs)
				_apply_widget_style(self.fields[field_name])

		left_fields = ['conj_nome', 'conj_documento']
		right_fields = ['conj_numero_rg', 'conj_orgao_emissor_rg']

		for field_name in left_fields:
			if field_name in self.fields:
				self.fields[field_name].widget.attrs['col'] = 'left'
		for field_name in right_fields:
			if field_name in self.fields:
				self.fields[field_name].widget.attrs['col'] = 'right'

		if self.instance and self.instance.pk:
			doc = self.instance.conj_documento
			if doc:
				if len(doc) == 11:
					self.initial['conj_documento'] = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
				elif len(doc) == 14:
					self.initial['conj_documento'] = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"


# ===================================================================
# FORM DOCUMENTOS — usado pelo endpoint separado uploadDocumentosCliente
# ===================================================================
class ClienteDocumentosForm(forms.ModelForm):

	class Meta:
		model = Cliente
		fields = [
			'foto_rg_frente', 'foto_rg_verso', 'foto_cpf',
			'comprovante_residencia', 'conj_rg_frente', 'conj_rg_verso',
			'certidao_estado_civil',
		]
		widgets = {
			'foto_rg_frente': forms.FileInput(),
			'foto_rg_verso': forms.FileInput(),
			'foto_cpf': forms.FileInput(),
			'comprovante_residencia': forms.FileInput(),
			'conj_rg_frente': forms.FileInput(),
			'conj_rg_verso': forms.FileInput(),
			'certidao_estado_civil': forms.FileInput(),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.required = False
			field.widget.attrs['class'] = 'glot-input'
			field.widget.attrs['accept'] = '.jpg,.jpeg,.png,.pdf'


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
			_apply_widget_style(field)

		self.fields['numero'].widget.attrs.update({
			'placeholder': 'Digite o telefone',
			'class': _merge_classes(self.fields['numero'].widget.attrs.get('class'), 'mask-phone'),
			'id': 'telefoneNumero',
		})
		if 'tipo' in self.fields:
			self.fields['tipo'].widget.attrs.update({
				'class': _merge_classes(self.fields['tipo'].widget.attrs.get('class'), 'glot-select'),
			})
		if 'observacao' in self.fields:
			self.fields['observacao'].widget.attrs.update({'placeholder': 'Observação'})

		colunas = {'numero': 'left', 'tipo': 'center', 'observacao': 'right'}
		for field, col in colunas.items():
			if field in self.fields:
				self.fields[field].widget.attrs['col'] = col
