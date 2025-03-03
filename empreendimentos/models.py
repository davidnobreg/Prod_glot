
from django.db import models
from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

## Cadastro de empreendimento
class Empreendimento(models.Model):
    
    id = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='empreendimento', verbose_name='Logo',
        null=True, blank=True)
    is_ativo = models.BooleanField(default=False)

    def __str__(self):
        #return self.nome
        return "{} - {} - ativo - {}".format(self.id, self.nome, self.is_ativo)
    
    class Meta:
        verbose_name = 'empreendimento'
        verbose_name_plural = 'Empreendimentos'
        ordering = ['id']
        
## Cadastro de Quadra
class Quadra(models.Model):
    
    id = models.BigAutoField(primary_key=True)
    namequadra = models.CharField(max_length=50)
    empr = models.ForeignKey(Empreendimento,on_delete=models.CASCADE, related_name='empreendimento')
    
     
    def __str__(self):
        return "{} - {}".format(self.empr.nome, self.namequadra)

## Opções de Imóveis
class TypeLote(models.TextChoices):
    DISPONIVEL = 'DISPONIVEL','DISPONIVEL' 
    RESEVADO = 'RESEVADO','RESEVADO'
    VENDIDO = 'VENDIDO','VENDIDO' 
    
class Lote(models.Model):
      
    id = models.BigAutoField(primary_key=True)  
    lote = models.CharField('Nome do Lote', max_length=50)
    area = models.CharField('ÁREA', max_length=50)
    situacao = models.CharField(max_length=100, choices=TypeLote.choices)
    quadra = models.ForeignKey(Quadra, on_delete=models.CASCADE, related_name='quadra')   
   
    def __str__(self):
        return "{}".format(self.lote)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['id']