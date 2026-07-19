from django.db import models

from .empreendimento import Empreendimento


## Cadastro de Quadra
class Quadra(models.Model):
    id = models.BigAutoField(primary_key=True)
    namequadra = models.CharField(max_length=50)

    empr = models.ForeignKey(Empreendimento, on_delete=models.CASCADE, related_name='empreendimento')
    def __str__(self):
        return "{}".format(self.namequadra)
