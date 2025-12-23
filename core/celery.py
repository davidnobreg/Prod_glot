from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Adicione explicitamente o módulo com a task
app.autodiscover_tasks([
    "empreendimentos.tasks",
    "vendas.tasks",
    "mensagem.tasks",
])