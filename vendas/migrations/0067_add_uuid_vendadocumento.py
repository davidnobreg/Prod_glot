import uuid

from django.db import migrations, models


def gerar_uuids(apps, schema_editor):
    VendaDocumento = apps.get_model("vendas", "VendaDocumento")
    for doc in VendaDocumento.objects.filter(uuid__isnull=True):
        doc.uuid = uuid.uuid4()
        doc.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("vendas", "0066_validar_arquivo_assinado_extensao"),
    ]

    operations = [
        migrations.AddField(
            model_name="vendadocumento",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gerar_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vendadocumento",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
