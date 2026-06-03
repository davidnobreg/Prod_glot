import os
from pathlib import Path

import pika
import pytest
from decouple import Config, RepositoryEnv, UndefinedValueError

ENV_PATH = Path(__file__).resolve().parent / "configuration" / ".env"


def test_rabbitmq_connection():
	if os.getenv("RUN_RABBITMQ_TEST") != "1":
		pytest.skip("Defina RUN_RABBITMQ_TEST=1 para testar conexao real com RabbitMQ")

	config = Config(repository=RepositoryEnv(ENV_PATH))

	try:
		user = config("RABBITMQ_USER")
		password = config("RABBITMQ_PASSWD")
		host = config("RABBITMQ_HOST")
		port = config("RABBITMQ_PORT")
		vhost = config("RABBITMQ_VHOST")
	except UndefinedValueError as exc:
		pytest.skip(str(exc))

	url = os.getenv(
		"CELERY_BROKER",
		f"amqp://{user}:{password}@{host}:{port}/{vhost}",
	)

	params = pika.URLParameters(url)
	connection = pika.BlockingConnection(params)
	connection.close()