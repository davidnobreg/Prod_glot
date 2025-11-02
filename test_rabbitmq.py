import pika
import os
from prettyconf import Configuration
from decouple import config

config_host = Configuration()


# Substitua com suas credenciais e host
user = config('RABBITMQ_USER')
password = config('RABBITMQ_PASSWD')
host = config('RABBITMQ_HOST')
port = config('RABBITMQ_PORT')
vhost = config('RABBITMQ_VHOST')


url = CELERY_BROKER_URL = os.getenv(
    'CELERY_BROKER',
    f'amqp://{user}:{password}@{host}:{port}/{vhost}'
)
# Substitua com suas credenciais e host


try:
    params = pika.URLParameters(url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    print("✅ Conexão com RabbitMQ OK")
    connection.close()
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
