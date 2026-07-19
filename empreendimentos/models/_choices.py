from django.db import models


choices_estado = (
    ('PB', 'Paraíba'), ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'),
    ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'),
    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('PR', 'Paraná'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'),
    ('SE', 'Sergipe'), ('TO', 'Tocantins')
)


class TypeBancos(models.TextChoices):
    BANCOBRASIL = '001', 'Banco do Brasil',
    BANCONORDESTE = '004', 'Banco do Nodeste',
    CAIXAECONOMICA = '104', 'Caixa Economica',
    SICOOB = '756', 'Sicoob',
    SINCRED = '748', 'Sincred',


class TypeLote(models.TextChoices):
    CONSTRUTORA = 'CONSTRUTORA', 'CONSTRUTORA',
    DISPONIVEL = 'DISPONIVEL', 'DISPONIVEL'
    EM_RESERVA = 'EM_RESERVA', 'EM_RESERVA'
    INDISPONIVEL = 'INDISPONIVEL', 'INDISPONIVEL'
    PRE_RESERVA = 'PRE-RESERVA', 'PRE-RESERVA'
    RESERVADO = 'RESERVADO', 'RESERVADO'
    PRE_VENDA = 'PRE-VENDA', 'PRE-VENDA'
    VENDIDO = 'VENDIDO', 'VENDIDO'
    ANALISE = 'ANALISE', 'ANALISE'


CHOICES_ESTADO_CIVIL = (
    ('solteiro', 'Solteiro'),
    ('casado', 'Casado'),
    ('divorciado', 'Divorciado'),
    ('viuvo', 'Viúvo'),
    ('separado_judicialmente', 'Separado judicialmente'),
    ('uniao_estavel', 'União estável'),
)
