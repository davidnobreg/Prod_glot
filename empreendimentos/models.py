from django.utils import timezone
from datetime import timedelta
from django.db import models


from django.contrib.auth.models import User



## Cadastro de empreendimento
class Empreendimento(models.Model):
    
    id = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    tempo_reserva = models.IntegerField(default=0)
    quantidade_parcela = models.IntegerField(default=0)
    logo = models.ImageField(verbose_name='Logo',
        null=True, blank=True)
    is_ativo = models.BooleanField(default=False)


    def __str__(self):
        #return self.nome
        return "{}".format(self.nome)
    
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
        return "{}".format(self.namequadra)

## Opções de Imóveis
class TypeLote(models.TextChoices):
    CONSTRUTORA = 'CONSTRUTORA','CONSTRUTORA',
    DISPONIVEL = 'DISPONIVEL','DISPONIVEL'
    EM_RESERVA = 'EM_RESERVA', 'EM_RESERVA'
    INDISPONIVEL = 'INDISPONIVEL', 'INDISPONIVEL',
    RESERVADO = 'RESERVADO','RESERVADO'
    VENDIDO = 'VENDIDO','VENDIDO' 
    
class Lote(models.Model):
      
    id = models.BigAutoField(primary_key=True)  
    lote = models.CharField('Nome do Lote', max_length=50)
    area = models.CharField('ÁREA', max_length=50)
    situacao = models.CharField(max_length=100, choices=TypeLote.choices)
    tempo_reservado = models.TimeField(default=timezone.now)
    quadra = models.ForeignKey(Quadra, on_delete=models.CASCADE, related_name='lotes')
    valor_metro_quadrado = models.CharField('Valor Metro Quadrado', max_length=50, default=00.00)

    def save(self, *args, **kwargs):
        self.tempo_reservado = timezone.localtime(timezone.now()) + timedelta(minutes=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return "{}".format( self.lote)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['id']