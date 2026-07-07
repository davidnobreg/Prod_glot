import uuid

from django.db import migrations, models


def gerar_uuids(apps, schema_editor):
    EmpreendimentoDocumento = apps.get_model("documentos", "EmpreendimentoDocumento")
    for vinculo in EmpreendimentoDocumento.objects.filter(uuid__isnull=True):
        vinculo.uuid = uuid.uuid4()
        vinculo.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("documentos", "0015_add_uuid_modelodocumento_documentogerado"),
    ]

    operations = [
        migrations.AddField(
            model_name="empreendimentodocumento",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gerar_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="empreendimentodocumento",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
