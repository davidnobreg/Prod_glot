FROM python:3.12-slim-trixie

# ===================================
# Variáveis de ambiente
# ===================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ===================================
# Diretório da aplicação
# ===================================
WORKDIR /app

# ===================================
# Dependências do sistema
# ===================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi-dev \
    libglib2.0-0 \
    shared-mime-info \
    fonts-dejavu \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ===================================
# Dependências Python
# ===================================
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ===================================
# Código da aplicação
# ===================================
COPY . .

# ===================================
# Diretórios persistentes
# ===================================
RUN mkdir -p \
    /app/logs \
    /app/media \
    /app/static \
    /app/configuration

# ===================================
# Porta
# ===================================
EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120"]