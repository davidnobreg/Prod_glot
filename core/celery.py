import os

from celery import Celery


# Define o arquivo de configurações padrão do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")


# Cria a aplicação Celery
app = Celery("core")


# Carrega as configurações do Celery a partir do settings.py
# Todas as configurações devem começar com CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")


# Descobre automaticamente os arquivos tasks.py dos apps Django
app.autodiscover_tasks()


# Rotas das filas do Celery
app.conf.task_routes = {
    "empreendimentos.tasks.*": {"queue": "empreendimentos"},
    "mensagem.tasks.*": {"queue": "mensagens"},
}


# Corrige aviso de depreciação do Celery
# Em caso de perda de conexão com o broker, cancela tarefas longas em execução
app.conf.worker_cancel_long_running_tasks_on_connection_loss = True