
import os
from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Adicione explicitamente o módulo com a task

app.autodiscover_tasks([
    "empreendimentos.tasks",
    "vendas.tasks",
    "mensagem.tasks",
])

# ==================================================
# EXCHANGE DO APP EMPREENDIMENTOS
# ==================================================

EMPREENDIMENTOS_EXCHANGE = Exchange(
    "app_empreendimentos",
    type="topic"
)

EMPREENDIMENTOS_DLX = Exchange(
    "app_empreendimentos.dlx",
    type="topic"
)

# ==================================================
# FILAS
# ==================================================

app.conf.task_queues = (
    Queue(
        "app_empreendimentos.default",
        exchange=Exchange("app_empreendimentos", type="direct"),
        routing_key="empreendimentos.tasks",
        queue_arguments={
            "x-dead-letter-exchange": "app_empreendimentos.dlx",
            "x-dead-letter-routing-key": "empreendimentos.dlq",
        },
    ),
)

app.conf.task_queues += (
    Queue(
        "app_empreendimentos.dlq",
        exchange=Exchange("app_empreendimentos.dlx", type="direct"),
        routing_key="empreendimentos.dlq",
    ),
)

# ==================================================
# ROTAS (APENAS EMPREENDIMENTOS)
# ==================================================

app.conf.task_routes = {
    "empreendimentos.tasks.*": {
        "queue": "app_empreendimentos.default",
        "routing_key": "empreendimentos.tasks",
    },
}

# ==================================================
# DEFAULTS (SEGUROS)
# ==================================================

app.conf.task_default_queue = "app_empreendimentos.default"
app.conf.task_default_exchange = "app_empreendimentos"
app.conf.task_default_exchange_type = "topic"
app.conf.task_default_routing_key = "empreendimentos.tasks"
