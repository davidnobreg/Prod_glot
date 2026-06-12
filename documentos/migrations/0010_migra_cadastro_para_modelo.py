# Numeração 0010: 0008/0009 pulados intencionalmente (reservados durante
# desenvolvimento paralelo das fases do módulo documentos). Sem impacto —
# Django resolve migrations pelo grafo de dependencies, não pela numeração.
from django.db import migrations
from django.conf import settings


def migrar_contratos(apps, schema_editor):
    Empreendimento = apps.get_model('empreendimentos', 'Empreendimento')
    ModeloDocumento = apps.get_model('documentos', 'ModeloDocumento')
    EmpreendimentoDocumento = apps.get_model('documentos', 'EmpreendimentoDocumento')

    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)

    usuario = (
        User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_active=True).first()
    )
    if not usuario:
        raise Exception('Nenhum usuario encontrado para criado_por.')

    for empr in Empreendimento.objects.select_related('contrato').filter(contrato__isnull=False):
        cadastro = empr.contrato
        modelo = ModeloDocumento.objects.filter(titulo=cadastro.titulo, tipo='contrato').first()
        if not modelo:
            modelo = ModeloDocumento.objects.create(
                titulo=cadastro.titulo,
                tipo='contrato',
                conteudo_html=cadastro.texto,
                eh_global=False,
                versao=cadastro.versao,
                ativo=cadastro.ativo,
                criado_por=usuario,
            )
        vinculo, created = EmpreendimentoDocumento.objects.get_or_create(
            empreendimento=empr,
            modelo=modelo,
            defaults={'padrao': True, 'ativo': True, 'ordem': 0},
        )
        if not created and not vinculo.padrao:
            vinculo.padrao = True
            vinculo.save(update_fields=['padrao'])


def reverter_migracao(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0007_seed_variaveis_documento'),
        ('empreendimentos', '0056_alter_lote_situacao'),
    ]

    operations = [
        migrations.RunPython(migrar_contratos, reverter_migracao),
    ]
