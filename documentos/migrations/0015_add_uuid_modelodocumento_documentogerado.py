import uuid

from django.db import migrations, models


def gerar_uuids(apps, schema_editor):
    ModeloDocumento = apps.get_model("documentos", "ModeloDocumento")
    for modelo in ModeloDocumento.objects.filter(uuid__isnull=True):
        modelo.uuid = uuid.uuid4()
        modelo.save(update_fields=["uuid"])

    DocumentoGerado = apps.get_model("documentos", "DocumentoGerado")
    for doc in DocumentoGerado.objects.filter(uuid__isnull=True):
        doc.uuid = uuid.uuid4()
        doc.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("documentos", "0014_add_variavel_qtd_parcelas_extenso"),
    ]

    operations = [
        migrations.AddField(
            model_name="modelodocumento",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="documentogerado",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gerar_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="modelodocumento",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
        migrations.AlterField(
            model_name="documentogerado",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
