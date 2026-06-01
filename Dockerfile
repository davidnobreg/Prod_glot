FROM python:3.12-slim-trixie

# ==========================================

# Variáveis de ambiente

# ==========================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ==========================================

# Diretório da aplicação

# ==========================================

WORKDIR /app

# ==========================================

# Dependências do sistema

# ==========================================

RUN apt-get update &&
apt-get install -y --no-install-recommends
gcc
build-essential
libpq-dev
libpango-1.0-0
libpangoft2-1.0-0
libgdk-pixbuf-2.0-0
libcairo2
libffi-dev
libglib2.0-0
shared-mime-info
fonts-dejavu &&
apt-get clean &&
rm -rf /var/lib/apt/lists/*

# ==========================================

# Dependências Python

# ==========================================

COPY requirements.txt .

RUN pip install --upgrade pip &&
pip install -r requirements.txt

# ==========================================

# Código da aplicação

# ==========================================

COPY . .

# ==========================================

# Diretórios persistentes

# ==========================================

RUN mkdir -p
/app/logs
/app/media
/app/configuration
/app/static

# ==========================================

# Entrypoint

# ==========================================

COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# ==========================================

# Porta

# ==========================================

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
