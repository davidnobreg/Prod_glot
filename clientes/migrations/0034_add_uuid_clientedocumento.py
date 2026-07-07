import uuid

from django.db import migrations, models


def gerar_uuids(apps, schema_editor):
    ClienteDocumento = apps.get_model("clientes", "ClienteDocumento")
    for doc in ClienteDocumento.objects.filter(uuid__isnull=True):
        doc.uuid = uuid.uuid4()
        doc.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("clientes", "0033_add_pertence_a_rg_novo"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientedocumento",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gerar_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="clientedocumento",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
