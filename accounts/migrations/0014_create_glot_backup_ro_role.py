from django.db import migrations

# Cria a role Postgres só-leitura usada pelo container glot-backup (pg_dump).
# NÃO define senha aqui — senha nunca vai pro git. A role fica NOLOGIN até
# a migration 0015 rodar (ela ativa o login automaticamente lendo
# GLOT_DB_PASSWORD do ambiente, toda vez que o Django migra).

CREATE_ROLE_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'glot_backup_ro') THEN
        CREATE ROLE glot_backup_ro NOLOGIN;
    END IF;
END
$$;

DO $$
DECLARE
    db_name text := current_database();
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO glot_backup_ro', db_name);
END
$$;

GRANT USAGE ON SCHEMA public TO glot_backup_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO glot_backup_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO glot_backup_ro;
"""

# Reverso só desfaz os GRANTs que esta migration deu. Não faz DROP ROLE:
# se alguém já rodou o ALTER ROLE ... LOGIN PASSWORD manual em produção,
# um DROP ROLE aqui destruiria isso sem aviso ao rodar migrate pra trás.
REVOKE_ROLE_SQL = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM glot_backup_ro;
REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM glot_backup_ro;
REVOKE USAGE ON SCHEMA public FROM glot_backup_ro;

DO $$
DECLARE
    db_name text := current_database();
BEGIN
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM glot_backup_ro', db_name);
END
$$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_add_uuid_user"),
    ]

    operations = [
        migrations.RunSQL(CREATE_ROLE_SQL, reverse_sql=REVOKE_ROLE_SQL),
    ]
