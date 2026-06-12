# Fix — Roteamento explícito de fila na task gerar_pdf_documento

## Contexto
A task `gerar_pdf_documento` em `documentos/tasks.py` não declara a fila
explicitamente — depende de `CELERY_TASK_DEFAULT_QUEUE = "empreendimentos"`
no settings. Isso é frágil: se o settings mudar ou a task for movida,
ela vai para a fila errada silenciosamente.

## Leia antes de alterar
```
documentos/tasks.py
core/settings.py  → buscar CELERY_TASK_ROUTES e CELERY_TASK_DEFAULT_QUEUE
```

---

## Opção A — queue no decorator da task (preferida)

```python
@shared_task(bind=True, max_retries=3, queue='empreendimentos')
def gerar_pdf_documento(self, documento_pk):
    ...
```

## Opção B — CELERY_TASK_ROUTES no settings (se já existir esse padrão)

```python
CELERY_TASK_ROUTES = {
    'documentos.tasks.gerar_pdf_documento': {'queue': 'empreendimentos'},
}
```

Verificar qual padrão já está sendo usado no projeto para outras tasks
(ex: tasks de mensagens) e seguir o mesmo.

---

## O que NÃO alterar
- Lógica da task
- Workers no docker-stack.yml
- Qualquer outro arquivo

---

## Entregáveis
Diff de `documentos/tasks.py` ou `core/settings.py` com o roteamento adicionado.
