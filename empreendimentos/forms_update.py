import re

from django.core.exceptions import ValidationError

from .forms import EmpreendimentoStep1Form, EmpresaStep2Form
from .models import Empreendimento


class EmpreendimentoUpdateStep1Form(EmpreendimentoStep1Form):
	"""Igual a EmpreendimentoStep1Form, mas a checagem de nome duplicado
	também exclui o pk do empreendimento REAL (não só o do draft que essa
	form está editando) — sem isso, manter o nome inalterado no wizard de
	update sempre bateria no próprio real e falsamente acusaria duplicata."""

	def __init__(self, *args, real_pk, **kwargs):
		self.real_pk = real_pk
		super().__init__(*args, **kwargs)

	def clean_nome(self):
		nome = self.cleaned_data.get('nome')
		if not nome:
			return nome

		qs = Empreendimento.objects.filter(nome__iexact=nome, is_ativo=True)
		qs = qs.exclude(pk=self.real_pk)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise ValidationError('Já existe um empreendimento ativo com este nome.')

		return nome


class EmpresaUpdateStep2Form(EmpresaStep2Form):
	"""Mesma correção de exclusão de real_pk, pro CNPJ."""

	def __init__(self, *args, real_pk, **kwargs):
		self.real_pk = real_pk
		super().__init__(*args, **kwargs)

	def validate_unique(self):
		"""Exclui cnpj da checagem automática de unicidade do model — clean_cnpj já
		faz essa validação corretamente (com a exclusão de real_pk). Os demais campos
		continuam sendo validados normalmente."""
		exclude = list(self._get_validation_exclusions())
		exclude.append('cnpj')
		try:
			self.instance.validate_unique(exclude=exclude)
		except ValidationError as e:
			self._update_errors(e)

	def clean_cnpj(self):
		cnpj = self.cleaned_data.get('cnpj')
		if not cnpj:
			return cnpj

		cnpj = re.sub(r'\D', '', cnpj)
		if len(cnpj) != 14:
			raise ValidationError('CNPJ deve conter exatamente 14 números.')

		qs = Empreendimento.objects.filter(cnpj=cnpj)
		qs = qs.exclude(pk=self.real_pk)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise ValidationError('Este CNPJ já está cadastrado.')

		return cnpj
