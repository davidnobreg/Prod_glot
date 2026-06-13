# GLOT — Grupos Configuráveis — Fase 2

## Contexto

A Fase 1 já criou:
- 24 permissões `glot_{modulo}_{acao}` via `post_migrate`
- 3 grupos seedados: `Administrador`, `Corretor`, `Proprietario`
- Management command `seed_grupos`

A Fase 2 implementa a tela de gerenciamento de grupos acessível pelo admin
via menu lateral de usuários. Padrão visual: **Tailwind** (mesmo padrão das
telas recentes do GLOT como `empreendimento.html`).

---

## Funcionalidades da tela

### Lista de grupos (`/usuarios/grupos/`)
- Tabela com: Nome do grupo, Qtd de permissões, Qtd de usuários, Ações
- Botão "Novo Grupo"
- Botão Editar e Excluir por linha
- Excluir só permitido se grupo não tiver usuários vinculados

### Criar/Editar grupo (`/usuarios/grupos/novo/` e `/usuarios/grupos/<id>/editar/`)
- Campo: Nome do grupo
- Tabela de checkboxes com permissões:
  - Linhas = módulos (Vendas, Clientes, Empreendimentos, Documentos, Relatórios, Usuários)
  - Colunas = ações (Ver, Criar, Editar, Excluir)
  - Checkbox "marcar todos" por linha e por coluna
- Botão Salvar e Cancelar

### Associar usuários a grupos (`/usuarios/<id>/grupos/`)
- Select2 ou similar para selecionar grupos
- Usuário pode pertencer a múltiplos grupos
- Exibir grupos atuais com botão para remover

---

## Implementação

### URLs — adicionar em `usuarios/urls.py`

```python
path('grupos/', views.lista_grupos, name='lista_grupos'),
path('grupos/novo/', views.criar_grupo, name='criar_grupo'),
path('grupos/<int:pk>/editar/', views.editar_grupo, name='editar_grupo'),
path('grupos/<int:pk>/excluir/', views.excluir_grupo, name='excluir_grupo'),
```

### Views — adicionar em `usuarios/views.py`

Todas as views protegidas com `@login_required` + verificação de grupo `Administrador`.

**`lista_grupos`**: lista todos os `Group` com anotação de `count` de permissões e usuários.

**`criar_grupo`** e **`editar_grupo`**: recebem POST com `nome` e lista de `permissoes[]`
(codenames). Usar `Group.objects.get_or_create`, limpar permissões antigas e adicionar
as novas via `group.permissions.set(...)`.

**`excluir_grupo`**: bloquear se `group.user_set.exists()`, retornar erro com mensagem.

### Constante de módulos — importar de `usuarios/apps.py`

```python
from usuarios.apps import MODULOS_GLOT, ACOES
```

Passar para o template como contexto para renderizar a tabela dinamicamente.

---

## Template

### `usuarios/templates/usuarios/lista_grupos.html`

Extend do base Tailwind do projeto. Tabela com:
```html
| Grupo         | Permissões | Usuários | Ações        |
| Administrador | 24         | 3        | Editar       |
| Corretor      | 9          | 5        | Editar       |
| Proprietario  | 3          | 2        | Editar       |
| Financeiro    | 12         | 1        | Editar/Excluir |
```
Grupos seedados (Administrador, Corretor, Proprietario) não exibem botão Excluir.

### `usuarios/templates/usuarios/form_grupo.html`

Tabela de checkboxes com JS para "marcar linha toda" e "marcar coluna toda":

```html
              | Ver | Criar | Editar | Excluir | [Todos]
Vendas        | [ ] |  [ ]  |  [ ]   |   [ ]   |   [ ]
Clientes      | [ ] |  [ ]  |  [ ]   |   [ ]   |   [ ]
Empreendimentos| [ ] |  [ ]  |  [ ]   |   [ ]   |   [ ]
Documentos    | [ ] |  [ ]  |  [ ]   |   [ ]   |   [ ]
Relatórios    | [ ] |  [ ]  |  [ ]   |   [ ]   |   [ ]
Usuários      | [ ] |  [ ]  |  [ ]   |   [ ]   |   [ ]
[Todos]       | [ ] |  [ ]  |  [ ]   |   [ ]   |
```

Cada checkbox com `name="permissoes[]"` e `value="glot_{modulo}_{acao}"`.

Na edição, marcar os checkboxes das permissões que o grupo já possui.

---

## Menu lateral

Localizar o template do menu lateral de usuários e adicionar item:

```html
<a href="{% url 'lista_grupos' %}">
  <i class="..."></i> Grupos de Acesso
</a>
```

Visível apenas para usuários do grupo `Administrador`.

---

## O que NÃO fazer

- Não alterar os grupos `Administrador`, `Corretor`, `Proprietario` seedados
- Não aplicar permissões nas views do sistema ainda (Fase 3)
- Não remover o sistema antigo de `rolepermissions` — conviver por ora
- Não usar o Django Admin — a tela deve ser dentro do GLOT

---

## Como testar

1. Acessar `/usuarios/grupos/` como Administrador
2. Criar um novo grupo "Financeiro" com ver+criar em Vendas e ver em Relatórios
3. Editar o grupo e adicionar editar em Clientes
4. Tentar excluir — deve funcionar (grupo sem usuários)
5. Criar outro grupo, associar um usuário e tentar excluir — deve bloquear com mensagem

---

## Arquivos esperados ao final

- `usuarios/urls.py` — 4 novas rotas
- `usuarios/views.py` — 4 novas views
- `usuarios/templates/usuarios/lista_grupos.html`
- `usuarios/templates/usuarios/form_grupo.html`
- Menu lateral atualizado com link "Grupos de Acesso"
