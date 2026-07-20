import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet():
	key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
	return Fernet(base64.urlsafe_b64encode(key))


class EncryptedFieldMixin:
	"""Criptografa o valor em repouso (Fernet). Coluna sempre TEXT, independente do max_length."""

	def get_internal_type(self):
		return 'TextField'

	def get_prep_value(self, value):
		value = super().get_prep_value(value)
		if value is None or value == '':
			return value
		return _fernet().encrypt(str(value).encode()).decode()

	def from_db_value(self, value, expression, connection):
		if value is None or value == '':
			return value
		try:
			return _fernet().decrypt(value.encode()).decode()
		except InvalidToken:
			return value


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
	pass


class EncryptedTextField(EncryptedFieldMixin, models.TextField):
	pass
