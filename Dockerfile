# --- Base image ---
FROM python:3.12-slim

RUN git clone --branch main https://github.com/davidnobreg/glot.git /app

# --- Diretório de trabalho ---
WORKDIR /app

# --- Copiar arquivo .env ---
#COPY .env /app/

# --- Copiar dependencias ---
COPY requirements.txt /app/

# --- Instala dependências Python ---
RUN pip install -r requirements.txt

# --- Instala pacotes de sistema necessários ---
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
