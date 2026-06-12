# Refatoração — Deploy com imagem imutável

## Objetivo
Remover o `git pull` do runtime e fazer o código entrar na imagem no build.
O container não deve saber que Git existe em tempo de execução.

## Contexto atual (problema)
O `entrypoint.sh` faz `git pull origin main` + `pip install` a cada vez que
um container sobe. Isso significa:
- A imagem buildada no CI não é o que roda em produção
- Se o GitHub estiver fora, o container não sobe
- `GIT_COMMIT` no environment não reflete o código real
- Build multiplataforma (`linux/amd64,linux/arm64`) é desperdiçado

## Leia antes de alterar
```
Dockerfile
entrypoint.sh (ou o bloco RUN echo no Dockerfile que o gera)
.github/workflows/deploy.yml
docker-stack.yml
```

---

## Alteração 1 — Dockerfile

### Remover
- O bloco `RUN echo '...' > /entrypoint.sh` inteiro
- A linha `ENTRYPOINT ["/entrypoint.sh"]`
- A linha `RUN git clone ...` (o código entra via contexto do build, não clone)

### Adicionar
- `COPY . /app` para copiar o código do repositório para dentro da imagem
- Um `entrypoint.sh` simples que só executa o comando recebido

### Resultado esperado do Dockerfile (estrutura):
```dockerfile
FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# dependências do sistema (manter igual ao atual)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 \
    libcairo2 libffi-dev libglib2.0-0 shared-mime-info \
    fonts-dejavu nano \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# dependências Python — instalar ANTES do COPY para aproveitar cache
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# código da aplicação
COPY . /app

# diretórios persistentes
RUN mkdir -p /app/logs /app/media /app/static /app/configuration

ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--timeout", "120"]
```

**Nota importante:** `COPY requirements.txt` antes de `COPY . /app` é
intencional — o Docker cacheia a camada de dependências enquanto o
requirements.txt não mudar, acelerando builds.

**Remover `git` do apt-get** — não é mais necessário no container de produção.
Verificar se algum outro serviço depende de git no container antes de remover.

---

## Alteração 2 — .github/workflows/deploy.yml

### Remover
- A busca do stack file via API do Portainer (`curl .../api/stacks/48/file`)
- O `python3 -c "import sys,json..."` de parsing

### Adicionar após o build+push
**Step: Enviar stack file do repositório**

O `docker-stack.yml` deve ser lido do repositório e enviado para o Portainer,
não o contrário.

```yaml
- name: Redeploy via API do Portainer
  env:
    GIT_COMMIT: ${{ github.sha }}
    PORTAINER_TOKEN: ${{ secrets.PORTAINER_TOKEN }}
    PORTAINER_URL: ${{ secrets.PORTAINER_URL }}
    SENTRY_DSN: ${{ secrets.SENTRY_DSN }}
  run: |
    set -e

    echo "Lendo stack file do repositório..."
    STACK_FILE_JSON=$(python3 -c "
    import json, sys
    with open('docker-stack.yml', 'r') as f:
        content = f.read()
    print(json.dumps(content))
    ")

    echo "Atualizando stack no Portainer..."
    RESPONSE=$(curl -s -o /tmp/portainer_response.json -w "%{http_code}" -X PUT \
      -H "X-API-Key: $PORTAINER_TOKEN" \
      -H "Content-Type: application/json" \
      "$PORTAINER_URL/api/stacks/48?endpointId=1" \
      -d "{
        \"stackFileContent\": $STACK_FILE_JSON,
        \"env\": [
          {\"name\": \"GIT_COMMIT\", \"value\": \"$GIT_COMMIT\"},
          {\"name\": \"SENTRY_DSN\",  \"value\": \"$SENTRY_DSN\"}
        ],
        \"pullImage\": true,
        \"prune\": true
      }")

    echo "Status: $RESPONSE"
    if [ "$RESPONSE" != "200" ]; then
      echo "Erro ao atualizar stack:"
      cat /tmp/portainer_response.json
      exit 1
    fi

    echo "Stack atualizada. Aguardando containers subirem..."
    sleep 20

    echo "Verificando saúde da aplicação..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      --max-time 15 \
      -H "Host: www.carlosecelsoimoveis.com.br" \
      "$PORTAINER_URL" || echo "000")

    # Health check via endpoint Django (ajustar se tiver /health/ implementado)
    # Por ora verifica se o container web respondeu ao Portainer
    echo "Deploy concluído. Commit: $GIT_COMMIT"
```

### Remover build multiplataforma
Trocar:
```yaml
platforms: linux/amd64,linux/arm64
```
Por:
```yaml
platforms: linux/amd64
```
Apenas se o servidor for `amd64`. Verificar com:
```bash
# No servidor via Portainer terminal
uname -m
# Se retornar x86_64 → amd64, remover arm64
```

---

## Alteração 3 — docker-stack.yml

Commitar o arquivo no repositório (se ainda não estiver).

Verificar se existe `.gitignore` bloqueando `docker-stack.yml` ou
`docker-compose*.yml`. Se sim, remover essa linha do `.gitignore`.

Confirmar que o arquivo tem a correção do volume de media já aplicada
(adicionada na sessão anterior):
```yaml
worker_empreendimentos:
  volumes:
    - media_compartilhada:/app/media  # deve estar presente
```

---

## Alteração 4 — .gitignore (verificar)

Garantir que estes arquivos NÃO estão no `.gitignore`:
- `docker-stack.yml`
- `docker-compose.yml`

E que estes continuam ignorados:
- `.env`
- `*.env`
- `configuration/`
- `media/`
- `staticfiles/`

---

## Ordem de execução

1. Alterar `Dockerfile` — remover git clone + entrypoint com git pull
2. Verificar `.gitignore` — garantir que docker-stack.yml está no repo
3. Alterar `docker-stack.yml` — confirmar volume media + commitar
4. Alterar `deploy.yml` — ler stack do repo, remover arm64 se servidor for amd64
5. Fazer commit e push para `main`
6. Acompanhar o Actions — o primeiro build será mais lento (sem cache de imagem),
   os seguintes serão rápidos (COPY requirements antes do COPY .)

---

## Validação após o deploy

```bash
# No terminal do container web via Portainer
echo $GIT_COMMIT
# Deve retornar o SHA exato do commit que disparou o deploy

python -c "import django; print(django.__version__)"
# Deve funcionar sem precisar de git pull

ls /app/manage.py
# Código deve estar dentro da imagem
```

## O que NÃO alterar
- `docker-compose.yml` da stack do NPM — está correto
- Configuração do NPM (location /media/) — está correto
- Volumes externos no Portainer — permanecem iguais
- Secrets do GitHub — permanecem iguais
- `command` do serviço web no docker-stack.yml — migrate continua rodando ali
