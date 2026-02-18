from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField

# Create your models here.
class CadastroDocumento(models.Model):
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título do Contrato"
    )

    texto = RichTextUploadingField(
        verbose_name="Texto do Contrato"
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ('aluguel', 'Contrato de Aluguel'),
            ('outros', 'Outros Papeis'),
            ('reserva', 'Contrato de Reserva'),
            ('venda', 'Contrato de Venda'),
        ]
    )
    versao = models.IntegerField(default=1)

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titulo