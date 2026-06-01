FROM python:3.12-slim-trixie

# ===================================
# Variáveis de ambiente
# ===================================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ===================================
# Diretório da aplicação
# ===================================
WORKDIR /app

# ===================================
# Dependências do sistema
# ===================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    gcc \
    nano \
    supervisor \
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
# Clona projeto
# ===================================

COPY . .

#RUN git clone --branch main https://github.com/davidnobreg/glot.git /app

# ===================================
# Atualiza pip
# ===================================
RUN pip install --upgrade pip

# ===================================
# Instala dependências Python
# ===================================
RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        echo "requirements.txt não encontrado"; \
    fi

# ===================================
# Diretórios persistentes
# ===================================
RUN mkdir -p \
    /app/logs \
    /app/media \
    /app/static \
    /app/configuration

# ===================================
# Script de inicialização
# ===================================
RUN echo '#!/bin/sh\n\
set -e\n\
\n\
cd /app\n\
\n\
echo "Atualizando código..."\n\
git reset --hard HEAD\n\
git clean -fd\n\
git pull origin main\n\
\n\
echo "Atualizando dependências..."\n\
pip install -r requirements.txt\n\
\n\
exec "$@"\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# ===================================
# Porta padrão
# ===================================
EXPOSE 8000

# ===================================
# Entrypoint
# ===================================
ENTRYPOINT ["/entrypoint.sh"]

# ===================================
# Comando padrão
# ===================================
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]