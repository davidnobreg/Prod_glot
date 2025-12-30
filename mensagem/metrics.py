# mensagem/metrics.py

from prometheus_client import Counter

mensagens_enviadas = Counter(
    "mensagens_enviadas_total",
    "Total de mensagens enviadas"
)

mensagens_falha = Counter(
    "mensagens_falha_total",
    "Total de falhas no envio"
)
