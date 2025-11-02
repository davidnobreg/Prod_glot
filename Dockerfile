# --- Base image ---
FROM python:3.12-slim

# --- Variáveis de ambiente globais ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- Diretório de trabalho ---
WORKDIR /app

# --- Instala pacotes de sistema necessários ---
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Clona o repositório do GitHub ---
RUN git clone --branch main https://github.com/davidnobreg/glot.git /app

# --- Instala dependências Python ---
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --- Expõe a porta do Gunicorn ---
EXPOSE 8000

# --- Comando padrão (Gunicorn) ---
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
