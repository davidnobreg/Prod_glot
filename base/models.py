import uuid

from django.db import models

CHOICES_ESTADO = (
	('PB', 'Paraíba'), ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
	('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'),
	('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'),
	('PE', 'Pernambuco'), ('PI', 'Piauí'), ('PR', 'Paraná'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
	('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'),
	('SE', 'Sergipe'), ('TO', 'Tocantins'),
)


class Endereco(models.Model):
	uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	cep = models.CharField(max_length=9)
	rua = models.CharField(max_length=255)
	numero = models.CharField(max_length=20)
	complemento = models.CharField(max_length=100, blank=True)
	bairro = models.CharField(max_length=100)
	cidade = models.CharField(max_length=100)
	estado = models.CharField(max_length=2, choices=CHOICES_ESTADO)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f'{self.rua}, {self.numero} - {self.cidade}/{self.estado}'

	class Meta:
		verbose_name = 'Endereço'
		verbose_name_plural = 'Endereços'
