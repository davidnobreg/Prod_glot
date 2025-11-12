# Usa Python 3.12 minimal
FROM python:3.12-slim-trixie

WORKDIR /app

# Instala dependências básicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc libpq-dev build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Clona o projeto (branch main)
RUN git clone --branch main https://github.com/davidnobreg/glot.git .

# Cria o arquivo .env (se não existir)
RUN if [ ! -f .env ]; then \
    echo "# ======================" > .env && \
    echo "# Django configuration" >> .env && \
    echo "# ======================" >> .env && \
    echo "SECRET_KEY=django-insecure-^-g*v!&(yc1dzs&qvkw5bhashtag#3se%!!ygiu-fm7oy01a)%7@wmeq9" >> .env && \
    echo "CSRF_TRUSTED_ORIGINS='https://django.carlosecelsoimoveis.com.br'" >> .env && \
    echo "ALLOWED_HOSTS = 'localhost,46.62.166.231,carlosecelsoimoveis.com.br,django.carlosecelsoimoveis.com.br'" >> .env && \
    echo "DEBUG=False" >> .env && \
    echo "" >> .env && \
    echo "# ======================" >> .env && \
    echo "# Database configuration" >> .env && \
    echo "# ======================" >> .env && \
    echo "DB_NAME=glot_new" >> .env && \
    echo "DB_USER=postgres" >> .env && \
    echo "DB_PASSWORD=JsA7hCka:*!#q?.hhi)1>wYV:~WjAH" >> .env && \
    echo "DB_HOST=postgres" >> .env && \
    echo "DB_PORT=5432" >> .env && \
    echo "" >> .env && \
    echo "# ======================" >> .env && \
    echo "# RabbitMQ configuration" >> .env && \
    echo "# ======================" >> .env && \
    echo "RABBITMQ_USER=carlosecelsoimoveis" >> .env && \
    echo "RABBITMQ_PASSWD=M3CRexzgkEafveXjq3ZuuB20eswbAr" >> .env && \
    echo "RABBITMQ_VHOST=carlosecelsoimoveis" >> .env && \
    echo "RABBITMQ_HOST=rabbitmq" >> .env && \
    echo "RABBITMQ_PORT=5672" >> .env && \
    echo "" >> .env && \
    echo "# ======================" >> .env && \
    echo "# Evolution API configuration" >> .env && \
    echo "# ======================" >> .env && \
    echo "EVOLUTION_API_URL=https://eapi.carlosecelsoimoveis.com.br/" >> .env && \
    echo "EVOLUTION_TOKEN=3EYi+%bhjzk-d5:sf@YVJpe=WrG?i}" >> .env && \
    echo "EVOLUTION_INSTANCE=carlosecelso" >> .env && \
    echo "" >> .env && \
    echo "# ======================" >> .env && \
    echo "# Repository info" >> .env && \
    echo "# ======================" >> .env && \
    echo "REPO_URL=https://github.com/davidnobreg/glot.git" >> .env && \
    echo "BRANCH=main" >> .env && \
    echo ".env criado com sucesso!"; \
    fi

# Instala dependências Python (se existir o arquivo)
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "Nenhum requirements.txt encontrado — pulando instalação."; \
    fi

EXPOSE 8000

CMD ["bash", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000 && celery -A core worker -l info && celery -A core beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler"]
