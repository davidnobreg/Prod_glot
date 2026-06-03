import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

# ==================================================
# CONFIG BASE
# ==================================================

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

<<<<<<< Updated upstream
app.autodiscover_tasks()
=======
app.conf.worker_proc_name = "glot_celery"
app.conf.task_create_missing_queues = False
app.conf.task_default_exchange_type = "direct"
app.conf.task_default_exchange = "app_empreendimentos"
app.conf.task_default_routing_key = "empreendimentos"
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
        name="app_empreendimentos.lotes",
        exchange=exchange_empreendimentos,
        routing_key="empreendimentos",
        durable=True,
        queue_arguments={
            "x-dead-letter-exchange": "app_empreendimentos.dlx",
            "x-dead-letter-routing-key": "empreendimentos.dlq",
        },
    ),

    Queue(
        name="app_empreendimentos.dlq",
        exchange=exchange_empreendimentos_dlx,
        routing_key="empreendimentos.dlq",
        durable=True,
    ),

    # ---------- MENSAGEM ----------
    Queue(
        name="app_mensagem.default",
        exchange=exchange_mensagem,
        routing_key="mensagem",
        durable=True,
        queue_arguments={
            "x-dead-letter-exchange": "app_mensagem.dlx",
            "x-dead-letter-routing-key": "mensagem.dlq",
        },
    ),

    Queue(
        name="app_mensagem.dlq",
        exchange=exchange_mensagem_dlx,
        routing_key="mensagem.dlq",
        durable=True,
    ),
)

# ==================================================
# ROTAS (MAPA DEFINITIVO)
# ==================================================
>>>>>>> Stashed changes

# 🔥 SÓ ISSO DE ROTEAMENTO
app.conf.task_routes = {
<<<<<<< Updated upstream
    "empreendimentos.tasks.*": {"queue": "empreendimentos"},
    "mensagem.tasks.*": {"queue": "mensagens"},
=======
    "empreendimentos.tasks.*": {
        "queue": "app_empreendimentos.lotes",
        "exchange": "app_empreendimentos",
        "routing_key": "empreendimentos",
    },
    "mensagem.tasks.*": {
        "queue": "app_mensagem.default",
        "exchange": "app_mensagem",
        "routing_key": "mensagem",
    },
>>>>>>> Stashed changes
}
