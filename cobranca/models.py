from django.db import models
from clientes.models import Cliente
from datetime import datetime

# Create your models here.

class TypeBoleto(models.TextChoices):
    GERADO = 'GERADO', 'GERADO'
    REGISTRADO = 'REGISTRADO', 'REGISTRADO'
    PAGO = 'PAGO', 'PAGO'
    CANCELADO = 'CANCELADO', 'CANCELADO'

class Cobranca(models.Model):

    id = models.BigAutoField(primary_key=True)
    cliente_id = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='cliente')
    valor_do_total = models.CharField('Valor toral sem correção', max_length=50, default=000.000,00)
    data_vencimento = models.DateField(default=datetime.now, blank=True)
    status_boleto = models.CharField(max_length=10, choices=TypeBoleto.choices)
    nosso_numero = models.CharField(max_length=100)
    cod_barras = models.CharField(max_length=100)
    linha_digitavel = models.CharField(max_length=100)
    url_pdf = models.ImageField(verbose_name='url_pdf',null=True, blank=True)
    is_ativo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = 'Cobranca'
        verbose_name_plural = 'Cobrancas'
        ordering = ['id']