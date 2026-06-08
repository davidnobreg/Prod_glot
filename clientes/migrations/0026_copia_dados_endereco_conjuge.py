from django.db import migrations


def copiar_dados(apps, schema_editor):
    ClienteEndereco = apps.get_model('clientes', 'ClienteEndereco')
    ClienteConjuge = apps.get_model('clientes', 'ClienteConjuge')

    for endereco in ClienteEndereco.objects.select_related('cliente').iterator():
        if endereco.cliente_id is None:
            continue
        cliente = endereco.cliente
        cliente.end_rua = endereco.rua
        cliente.end_complemento = endereco.complemento
        cliente.end_numero = endereco.numero
        cliente.end_bairro = endereco.bairro
        cliente.end_cep = endereco.cep
        cliente.end_cidade = endereco.cidade
        cliente.end_estado = endereco.estado
        cliente.save(update_fields=[
            'end_rua', 'end_complemento', 'end_numero', 'end_bairro',
            'end_cep', 'end_cidade', 'end_estado',
        ])

    for conjuge in ClienteConjuge.objects.select_related('cliente').iterator():
        if conjuge.cliente_id is None:
            continue
        cliente = conjuge.cliente
        cliente.conj_nome = conjuge.nome_conjuge
        cliente.conj_numero_rg = conjuge.numero_rg_conjuge
        cliente.conj_orgao_emissor_rg = conjuge.orgao_emissor_rg_conjuge
        cliente.conj_documento = conjuge.documento_conjuge
        cliente.save(update_fields=[
            'conj_nome', 'conj_numero_rg', 'conj_orgao_emissor_rg', 'conj_documento',
        ])


def reverter_dados(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    Cliente.objects.update(
        end_rua=None,
        end_complemento=None,
        end_numero=None,
        end_bairro=None,
        end_cep=None,
        end_cidade=None,
        end_estado=None,
        conj_nome=None,
        conj_numero_rg=None,
        conj_orgao_emissor_rg=None,
        conj_documento=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0025_incorpora_endereco_conjuge_no_cliente'),
    ]

    operations = [
        migrations.RunPython(copiar_dados, reverse_code=reverter_dados),
    ]