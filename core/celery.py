from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Configura o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Instancia o Celery
app = Celery('core')

# Usando string aqui significa que o Celery vai procurar o Django settings
# para que possamos configurar o Celery dentro do arquivo settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carrega os módulos de tarefas assíncronas (tasks)
app.autodiscover_tasks()
