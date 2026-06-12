# Fix — Redirect infinito em documento_detalhe

## Contexto
Em `documentos/views_gerar.py`, a view `documento_detalhe` redireciona
para ela mesma quando o usuário não tem permissão para o tipo do documento:

```python
# views_gerar.py ~linha 125
if doc.modelo.tipo not in tipos_ok:
    messages.error(request, 'Você não tem permissão...')
    return redirect('documentos:documento-detalhe', pk=pk)  # ← loop infinito
```

---

## Leia antes de alterar

```
documentos/views_gerar.py   → view documento_detalhe completa
documentos/models.py        → DocumentoGerado → FK venda
vendas/urls.py              → confirmar o name da URL de detalhe da venda
```

Precisamos saber: `DocumentoGerado` tem FK direta para `venda`?
E qual é o name da URL de detalhe da venda (ex: `vendas:reservado-detalhe`,
`vendas:analise-detalhe` etc)?

---

## Correção

Substituir o redirect para si mesmo por redirect à venda do documento.
Se não for possível (venda nula), retornar 403.

```python
# ANTES
if doc.modelo.tipo not in tipos_ok:
    messages.error(request, 'Você não tem permissão...')
    return redirect('documentos:documento-detalhe', pk=pk)

# DEPOIS
if doc.modelo.tipo not in tipos_ok:
    messages.error(request, 'Você não tem permissão para visualizar este documento.')
    if doc.venda_id:
        return redirect('vendas:reservado-detalhe', pk=doc.venda.pk)
    return HttpResponseForbidden('Acesso negado.')
```

Ajustar o name da URL conforme o que existir em `vendas/urls.py`.
Importar `HttpResponseForbidden` se não estiver importado:

```python
from django.http import HttpResponseForbidden
```

---

## Validação

1. Logar como Corretor
2. Tentar acessar diretamente a URL de um `DocumentoGerado` do tipo `contrato`
   (tipo que Corretor não tem permissão)
3. Deve redirecionar para a página da venda com mensagem de erro — não loop
4. Confirmar no browser que não há redirect infinito (DevTools → Network)

---

## Entregáveis
1. Diff de `documentos/views_gerar.py` com o redirect corrigido
2. Confirmação do name de URL usado para redirecionar à venda
