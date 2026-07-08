from django.db import migrations

# 0014 deu GRANT SELECT ON ALL TABLES IN SCHEMA public -- mas no Postgres
# "ALL TABLES" NÃO inclui sequences (precisa de GRANT separado). Descoberto
# rodando o backup de verdade em produção: pg_dump falhava com "permission
# denied for sequence accounts_user_groups_id_seq" ao tentar ler
# last_value/is_called da sequence.

GRANT_SQL = """
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO glot_backup_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO glot_backup_ro;
"""

REVOKE_SQL = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON SEQUENCES FROM glot_backup_ro;
REVOKE SELECT ON ALL SEQUENCES IN SCHEMA public FROM glot_backup_ro;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_set_glot_backup_ro_password"),
    ]

    operations = [
        migrations.RunSQL(GRANT_SQL, reverse_sql=REVOKE_SQL),
    ]
