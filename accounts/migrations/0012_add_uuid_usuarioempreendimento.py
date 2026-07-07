import uuid

from django.db import migrations, models


def gerar_uuids(apps, schema_editor):
    UsuarioEmpreendimento = apps.get_model("accounts", "UsuarioEmpreendimento")
    for vinculo in UsuarioEmpreendimento.objects.filter(uuid__isnull=True):
        vinculo.uuid = uuid.uuid4()
        vinculo.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_alter_user_tipo_usuario"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuarioempreendimento",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gerar_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="usuarioempreendimento",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
