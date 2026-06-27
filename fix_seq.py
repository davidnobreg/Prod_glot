from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT setval('django_admin_log_id_seq', (SELECT MAX(id) FROM django_admin_log) + 1)")
print("OK")
