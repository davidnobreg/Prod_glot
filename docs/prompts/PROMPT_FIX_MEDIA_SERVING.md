# Fix — Erro 500 no PDF gerado (media serving)

## Contexto
Nginx já tem `location /media/` apontando para `/app/media/`.
O arquivo existe no disco (confirmado na sessão anterior).
Causa mais provável: **o volume de media não está montado no serviço nginx**,
então o nginx serve um diretório vazio ou inexistente.

---

## Diagnóstico obrigatório — leia antes de alterar qualquer coisa

### 1. Verificar volumes no docker-compose / docker-stack
```
Leia o arquivo docker-compose.yml (ou docker-stack.yml).
Para cada serviço, liste os volumes montados.
Responda:
- O serviço `web` (Django) monta o volume de media? Em qual path?
- O serviço `nginx` monta o mesmo volume de media? Em qual path?
- Existe um named volume declarado na seção `volumes:` para media?
```

### 2. Verificar MEDIA_ROOT no settings
```
Leia core/settings.py.
Qual é o valor de MEDIA_ROOT?
É /app/media ou outro caminho?
```

### 3. Verificar o nginx.conf completo
```
Leia o nginx.conf atual completo.
O bloco já existente é:
    location /media/ {
        alias /app/media/;
    }
Confirmar que está dentro do bloco server {} correto
e que não há outro bloco sobrescrevendo.
```

---

## Correção esperada

O problema quase certamente é que o serviço `nginx` no compose
não monta o volume de media. A correção é adicionar o volume:

```yaml
# docker-compose.yml ou docker-stack.yml

services:
  web:
    volumes:
      - media_volume:/app/media   # já deve existir

  nginx:
    volumes:
      - media_volume:/app/media:ro  # adicionar isto — mesmo volume, read-only

volumes:
  media_volume:   # garantir que está declarado aqui
```

O path `/app/media` deve ser idêntico ao `alias` do nginx.conf
e ao `MEDIA_ROOT` do Django. Se forem diferentes, alinhar.

---

## Validação após a correção

### Sem precisar de deploy — testar via Portainer terminal

No terminal do container **nginx**:
```bash
ls /app/media/documentos/pdf/
# Deve listar os arquivos PDF gerados
# Se retornar "No such file or directory" → volume não está montado
```

No terminal do container **web**:
```bash
ls /app/media/documentos/pdf/
# Deve listar os mesmos arquivos
```

### Após corrigir o compose e fazer redeploy
```bash
# No terminal do container nginx
curl -I http://localhost/media/documentos/pdf/2026/06/PRP-2026-XXXX.pdf
# Esperado: HTTP/1.1 200 OK
# Content-Type: application/pdf
```

Substituir `PRP-2026-XXXX.pdf` por um arquivo real listado no `ls` acima.

---

## Entregáveis
1. Confirmação de qual volume estava faltando no serviço nginx
2. Diff do docker-compose.yml / docker-stack.yml com o volume adicionado
3. Output do `ls /app/media/documentos/pdf/` dentro do container nginx
   confirmando que os arquivos ficaram visíveis após o redeploy
