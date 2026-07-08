import os

from django.db import migrations

# Ativa o login da role glot_backup_ro (criada NOLOGIN em 0014) lendo a
# senha de GLOT_DB_PASSWORD no ambiente do serviço web (ver Docker-compose.yml
# e .github/workflows/deploy.yml). Roda a cada `migrate` — idempotente
# (ALTER ROLE com a mesma senha não tem efeito colateral). Se a variável não
# estiver setada (dev local, CI de teste), não faz nada — role continua
# NOLOGIN, sem quebrar a migration.


def set_password(apps, schema_editor):
    password = os.environ.get("GLOT_DB_PASSWORD")
    if not password:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER ROLE glot_backup_ro WITH LOGIN PASSWORD %s", [password]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_create_glot_backup_ro_role"),
    ]

    operations = [
        migrations.RunPython(set_password, migrations.RunPython.noop),
    ]
