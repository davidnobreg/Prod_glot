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
    nano \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ===================================
# Fonte Times New Roman (msttcorefonts) — documento_a4.css usa Times New
# Roman como padrão; sem isso o container substitui por outra fonte,
# fazendo o PDF renderizar diferente do editor (Windows tem a fonte real).
# "contrib" precisa ser habilitado — imagens Debian trixie só trazem "main".
# ===================================
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/^Components: main$/Components: main contrib/' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/ main$/ main contrib/' /etc/apt/sources.list; \
    fi && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get update && \
    apt-get install -y --no-install-recommends cabextract wget ttf-mscorefonts-installer && \
    fc-cache -f && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ===================================
# Dependências Python (cache-friendly)
# ===================================
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ===================================
# Chromium (Playwright) + deps de sistema
# ===================================
RUN playwright install --with-deps chromium

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
# Commit hash injetado no build
# ===================================
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

# ===================================
# Entrypoint + CMD
# ===================================
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
