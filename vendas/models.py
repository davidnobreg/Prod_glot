from django.db import models
from datetime import datetime
from clientes.models import Cliente
from empreendimentos.models import Lote, Empreendimento
from accounts.models import User

class TypeLote(models.TextChoices):
    CANCELADA = 'CANCELADA', 'CANCELADA'
    RESERVADO = 'RESERVADO', 'RESERVADO'
    VENDIDO = 'VENDIDO', 'VENDIDO'

## Registrar Venda

class RegisterVenda(models.Model):

    id = models.BigAutoField(primary_key=True)
    lote = models.OneToOneField(Lote, on_delete=models.SET_NULL, blank=True, null=True, related_name='reg_venda')
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, blank=True, null=True)
    tipo_venda = models.CharField(max_length=100, choices=TypeLote.choices)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="vendas")
    dt_reserva = models.DateField(default=datetime.now, blank=True)
    dt_venda = models.DateField(blank=True, null=True)
    create_at = models.DateField(default=datetime.now, blank=True)
    is_ativo = models.BooleanField(default=False)

    def __str__(self):
        return "{} - lote {} quadra- {} - {} - status {}".format(self.cliente, self.lote, self.lote.quadra.namequadra,
                                                     self.lote.quadra.empr, self.tipo_venda)

    class Meta:
        verbose_name = 'Registrar Venda'
        verbose_name_plural = 'Registrar Venda'
        ordering = ['-id']
