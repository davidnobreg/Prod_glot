# Fix — Unificar _tipos_permitidos nos detail_views

## Contexto
A lógica de filtrar tipos de documento por role está duplicada:
- `documentos/views_gerar.py` → função `_tipos_permitidos(user)` (fonte da verdade)
- `vendas/views/detail_views.py` → lógica inline equivalente em `AnaliseView`
  e `ReservadoDetalheView`

Se as regras de permissão mudarem no futuro, precisaria atualizar em dois lugares.

## Leia antes de alterar
```
documentos/views_gerar.py   → função _tipos_permitidos completa
vendas/views/detail_views.py → lógica inline em AnaliseView e ReservadoDetalheView
```

---

## Correção

### 1. Em `vendas/views/detail_views.py`

Adicionar import:
```python
from documentos.views_gerar import _tipos_permitidos
```

Substituir a lógica inline pelo import em ambas as views (`AnaliseView`
e `ReservadoDetalheView`):

```python
# ANTES (lógica inline — remover)
if user.tipo_usuario == 'ADMINISTRADOR':
    tipos = [...]
elif user.tipo_usuario == 'CORRETOR':
    tipos = ['proposta']
else:
    tipos = []

# DEPOIS (importado)
tipos = _tipos_permitidos(self.request.user)
```

### 2. Não alterar `views_gerar.py`
A função `_tipos_permitidos` permanece onde está — ela é a fonte da verdade.

---

## Validação
Confirmar que `modelos_por_tipo` no contexto de `AnaliseView` e
`ReservadoDetalheView` continua funcionando igual após a troca.

## Entregáveis
Diff de `vendas/views/detail_views.py` mostrando o import adicionado
e a lógica inline removida nas duas views.
