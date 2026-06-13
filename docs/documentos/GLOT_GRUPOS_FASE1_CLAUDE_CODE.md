# GLOT — Grupos Configuráveis — Fase 1

## Contexto

O sistema hoje tem 3 grupos fixos hardcoded: `Administrador`, `Corretor`, `Proprietario`.
O objetivo é manter esses grupos, mas torná-los configuráveis pelo admin via UI (Fase 2).
A Fase 1 prepara toda a base sem quebrar nada que já existe.

---

## Tarefas

### 1. Registrar permissões customizadas no `post_migrate`

Em `usuarios/apps.py`, adicionar um signal `post_migrate` que cria as permissões
do GLOT automaticamente após cada migrate.

As permissões seguem o padrão `glot_{modulo}_{acao}`:

```python
MODULOS_GLOT = [
    ("vendas", "Vendas"),
    ("clientes", "Clientes"),
    ("empreendimentos", "Empreendimentos"),
    ("documentos", "Documentos"),
    ("relatorios", "Relatórios"),
    ("usuarios", "Usuários"),
]

ACOES = ["ver", "criar", "editar", "excluir"]
```

Usar `ContentType` do model `User` (ou outro model fixo do projeto) como ancora.
Usar `Permission.objects.get_or_create` — idempotente, pode rodar múltiplas vezes.

Registrar o signal no `ready()` do `UsuariosConfig`.

---

### 2. Seed dos 3 grupos existentes

Criar um management command `usuarios/management/commands/seed_grupos.py`
que popula os grupos com as permissões padrão abaixo.

**Administrador** — acesso total:
- Todos os módulos: ver, criar, editar, excluir

**Corretor** — acesso operacional:
- vendas: ver, criar
- clientes: ver, criar, editar
- empreendimentos: ver
- documentos: ver, criar
- relatorios: ver

**Proprietario** — acesso somente leitura:
- vendas: ver
- empreendimentos: ver
- relatorios: ver

O command deve ser idempotente: se o grupo já existe, apenas sincroniza as permissões
(adiciona o que falta, não remove o que foi customizado manualmente).

Usar `Group.objects.get_or_create` e `group.permissions.add()`.

---

### 3. Verificar se `usuarios/apps.py` já existe

- Se existir, apenas adicionar o signal `post_migrate` e o `ready()` sem quebrar o que já tem.
- Se não existir, criar do zero com `default_auto_field` e o `name` correto do app.

---

### 4. Garantir que o app `usuarios` está em `INSTALLED_APPS`

Verificar em `settings.py` — se já estiver, não alterar.

---

## O que NÃO fazer

- Não remover nem alterar os grupos existentes no banco
- Não aplicar `@permission_required` em nenhuma view ainda (isso é Fase 2)
- Não criar migrations — as permissões são criadas via signal, não via migration
- Não alterar models existentes

---

## Como testar após implementar

```bash
python manage.py migrate  # deve disparar o signal e criar as permissões
python manage.py seed_grupos  # deve criar/atualizar os 3 grupos

# Verificar no shell:
python manage.py shell
>>> from django.contrib.auth.models import Permission, Group
>>> Permission.objects.filter(codename__startswith='glot_').count()  # deve ser 24
>>> Group.objects.values_list('name', flat=True)
>>> Group.objects.get(name='Corretor').permissions.all()
```

---

## Arquivos esperados ao final

- `usuarios/apps.py` — com signal `post_migrate` e `ready()`
- `usuarios/management/__init__.py`
- `usuarios/management/commands/__init__.py`
- `usuarios/management/commands/seed_grupos.py`
