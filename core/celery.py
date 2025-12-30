import os
from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks([
    "empreendimentos",
    "mensagem",
    # "vendas",
])

app.conf.worker_proc_name = "glot_celery_empreendimentos"
app.conf.task_create_missing_queues = False
app.conf.task_default_exchange_type = "direct"
app.conf.task_default_queue = "app_empreendimentos.lotes"
app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

# ==================================================
# EXCHANGES
# ==================================================

exchange_empreendimentos = Exchange(
    "app_empreendimentos",
    type="direct",
    durable=True,
)

exchange_empreendimentos_dlx = Exchange(
    "app_empreendimentos.dlx",
    type="direct",
    durable=True,
)

# ==================================================
# EXCHANGES - MENSAGEM
# ==================================================

exchange_mensagem = Exchange(
    "app_mensagem",
    type="direct",
    durable=True,
)

exchange_mensagem_dlx = Exchange(
    "app_mensagem.dlx",
    type="direct",
    durable=True,
)

# ==================================================
# FILAS
# ==================================================

app.conf.task_queues = (

    # ---------- EMPREENDIMENTOS ----------
    Queue(
        "app_empreendimentos.lotes",
        exchange=exchange_empreendimentos,
        routing_key="empreendimentos",
        durable=True,
        auto_delete=True,
        queue_arguments={
            "x-expires": 600000,  # 10 minutos
            "x-dead-letter-exchange": "app_empreendimentos.dlx",
            "x-dead-letter-routing-key": "empreendimentos.dlq",
        },
    ),

    Queue(
        "app_empreendimentos.dlq",
        exchange=exchange_empreendimentos_dlx,
        routing_key="empreendimentos.dlq",
        durable=True,
    ),

    # ---------- MENSAGEM ----------
    Queue(
        "app_mensagem.default",
        Exchange("app_mensagem", type="direct"),
        routing_key="mensagem",
        queue_arguments={
            "x-dead-letter-exchange": "app_mensagem.dlx",
            "x-dead-letter-routing-key": "mensagem.dlq",
        },
    ),
    Queue(
        "app_mensagem.dlq",
        Exchange("app_mensagem.dlx", type="direct"),
        routing_key="mensagem.dlq",
    ),
)

# ==================================================
# ROTAS (AQUI É O MAPA REAL)
# ==================================================

app.conf.task_routes = {
    "empreendimentos.tasks.*": {
        "queue": "app_empreendimentos.lotes",
        "routing_key": "empreendimentos",
    },
    "mensagem.tasks.*": {
        "queue": "app_mensagem.default",
        "routing_key": "mensagem",
        "exchange": "app_mensagem",
    }
}

# ==================================================
# DEFAULTS (NEUTROS, NÃO TRAI O SISTEMA)
# ==================================================
