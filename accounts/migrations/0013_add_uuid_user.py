import uuid

from django.db import migrations, models


def gerar_uuids(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for usuario in User.objects.filter(uuid__isnull=True):
        usuario.uuid = uuid.uuid4()
        usuario.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_add_uuid_usuarioempreendimento"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gerar_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
