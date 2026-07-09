import re

from django.core.exceptions import ValidationError

EXTENSOES_DOCUMENTO_REPRESENTANTE = ('pdf', 'jpg', 'jpeg', 'png')
TAMANHO_MAXIMO_DOCUMENTO_REPRESENTANTE = 10 * 1024 * 1024  # 10MB, mesmo padrão de vendas.VendaDocumento


def validar_cpf(documento: str) -> bool:
	"""Valida CPF (11 dígitos). Extraída de clientes.forms.clean_documento (implementação
	original, não a de Cliente.validar_cpf, que está morta e pode ter divergido)."""
	documento = re.sub(r'[^0-9]', '', documento or '')
	if len(documento) != 11 or documento == documento[0] * 11:
		return False
	soma = sum(int(documento[i]) * (10 - i) for i in range(9))
	dig1 = (soma * 10 % 11) % 10
	if dig1 != int(documento[9]):
		return False
	soma = sum(int(documento[i]) * (11 - i) for i in range(10))
	dig2 = (soma * 10 % 11) % 10
	return dig2 == int(documento[10])


def validate_documento_representante(value):
	"""Extensão + tamanho do arquivo de RepresentanteDocumento.

	Implementação local (não importa de vendas.models.validate_documento_assinado)
	pra não criar dependência clientes → vendas: vendas já depende de clientes
	via FK (RegisterVenda.cliente), inverter criaria acoplamento circular.
	"""
	ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
	if ext not in EXTENSOES_DOCUMENTO_REPRESENTANTE:
		raise ValidationError('Envie PDF, JPG ou PNG.')
	if value.size > TAMANHO_MAXIMO_DOCUMENTO_REPRESENTANTE:
		raise ValidationError('Arquivo não pode exceder 10 MB.')
