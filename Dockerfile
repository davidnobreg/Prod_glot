# Dockerfile
FROM python:3.12-slim

# Evita arquivos .pyc e buffer de logs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instala git e dependências do sistema
RUN apt-get update && apt-get install -y git && apt-get clean

# Argumentos para clonar o Git
ARG REPO_URL
ARG BRANCH=main

# Clona o repositório
RUN git clone --branch $BRANCH $REPO_URL /app

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expondo porta para Gunicorn
EXPOSE 8000

# Comando padrão para produção
CMD ["gunicorn", "meu_projeto.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2"]
