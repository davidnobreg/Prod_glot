# Fix — Status ERRO em StatusDocumento + task Celery + polling template

## Contexto
Quando a task `gerar_pdf_documento` falha após 3 retries, o documento fica
em `RASCUNHO` permanentemente sem nenhum feedback ao usuário.
Causa: `StatusDocumento` não tem o choice `ERRO` e o `except` da task
reverte para `RASCUNHO` em vez de marcar como erro.

---

## Arquivos a ler antes de alterar

```
documentos/models.py        → enum StatusDocumento
documentos/tasks.py         → task gerar_pdf_documento, bloco except
documentos/templates/documentos/documento_detalhe.html → script de polling
```

---

## Correções

### 1. Adicionar ERRO ao enum StatusDocumento
**`documentos/models.py`**

```python
class StatusDocumento(models.TextChoices):
    RASCUNHO     = 'rascunho',    'Rascunho'
    PROCESSANDO  = 'processando', 'Processando'
    FINALIZADO   = 'finalizado',  'Finalizado'
    CANCELADO    = 'cancelado',   'Cancelado'
    SUBSTITUIDO  = 'substituido', 'Substituído'
    ERRO         = 'erro',        'Erro'          # ← adicionar
```

### 2. Gerar migration
```bash
python manage.py makemigrations documentos --name="add_status_erro_documento"
```

Confirmar que a migration gerada é apenas uma `AlterField` no campo `status`
de `DocumentoGerado`. Não deve alterar nenhum outro model.

### 3. Corrigir o except na task
**`documentos/tasks.py`**

```python
# ANTES
except Exception as exc:
    doc.status = StatusDocumento.RASCUNHO
    doc.save(update_fields=['status'])
    raise self.retry(exc=exc)

# DEPOIS
except Exception as exc:
    try:
        self.retry(exc=exc)
    except self.MaxRetriesExceededError:
        doc.status = StatusDocumento.ERRO
        doc.save(update_fields=['status'])
        raise
    doc.status = StatusDocumento.RASCUNHO
    doc.save(update_fields=['status'])
    raise self.retry(exc=exc)
```

Forma mais limpa — marcar ERRO apenas quando esgotarem os retries:

```python
except Exception as exc:
    if self.request.retries >= self.max_retries:
        doc.status = StatusDocumento.ERRO
        doc.save(update_fields=['status'])
    else:
        doc.status = StatusDocumento.RASCUNHO
        doc.save(update_fields=['status'])
    raise self.retry(exc=exc)
```

Usar a forma que se encaixar melhor na estrutura atual da task.

### 4. Corrigir o polling no template
**`documentos/templates/documentos/documento_detalhe.html`**

O script de polling atualmente para apenas quando status é `finalizado` ou `cancelado`.
Adicionar `erro` como condição de parada e exibir mensagem ao usuário:

```javascript
// Dentro do script de polling — localizar o bloco de verificação de status
// e adicionar o tratamento de erro:

if (data.status === 'finalizado') {
    location.reload();
} else if (data.status === 'cancelado') {
    location.reload();
} else if (data.status === 'erro') {          // ← adicionar
    clearInterval(pollInterval);
    // Exibir mensagem de erro visível ao usuário
    document.getElementById('status-mensagem').textContent =
        'Falha ao gerar o PDF. Tente finalizar novamente ou contate o suporte.';
    document.getElementById('status-mensagem').style.display = 'block';
} else {
    // continua polling
}
```

Se não existir um elemento `#status-mensagem` no template, adicionar próximo
ao iframe de preview:

```html
<div id="status-mensagem"
     style="display:none; color: var(--bs-danger); padding: 0.75rem 1rem;
            background: #fff3f3; border-radius: 6px; margin-top: 1rem;">
</div>
```

---

## Validação

### Simular falha da task (ambiente de dev)
```python
# Temporariamente no tasks.py, forçar exceção:
raise Exception("teste de erro")
```

1. Finalizar um documento
2. Aguardar polling
3. Após `max_retries` esgotados, documento deve ficar com `status = 'erro'`
4. Template deve parar de pollar e exibir a mensagem de erro
5. Reverter o `raise Exception` após validar

### Verificar via shell
```bash
python manage.py shell
>>> from documentos.models import DocumentoGerado, StatusDocumento
>>> DocumentoGerado.objects.filter(status=StatusDocumento.ERRO).count()
# Deve retornar 0 inicialmente (ou o count correto após o teste)
```

---

## Entregáveis
1. Diff de `documentos/models.py` com `ERRO` adicionado ao enum
2. Migration gerada (`add_status_erro_documento`)
3. Diff de `documentos/tasks.py` com o `except` corrigido
4. Diff de `documento_detalhe.html` com polling atualizado e mensagem de erro
