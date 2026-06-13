# GLOT — Fase 3 — Proteção de Views + Impersonate

## Contexto

As permissões `glot_{modulo}_{acao}` já foram criadas na Fase 1.
Os grupos já estão seedados com as permissões corretas.
Esta fase aplica a proteção em todas as views do sistema e implementa
a funcionalidade de impersonate (acessar como outro usuário).

Comportamento: usuário sem permissão → redirecionar para login.

---

## Passo 1 — Levantamento (obrigatório antes de alterar)

```bash
find . -name "urls.py" -not -path "*/.venv/*" -not -path "*/migrations/*"
```

Para cada app, identificar as views e classificar por ação:
- Lista/listagem → `ver`
- Detalhe → `ver`
- Criar/novo → `criar`
- Editar/atualizar → `editar`
- Excluir/deletar → `excluir`
- Relatório/exportar → `ver` (relatorios)

Reportar o mapeamento completo antes de continuar.

---

## Passo 2 — Criar decorator e mixin utilitários

Criar `core/decorators.py` (ou `usuarios/decorators.py` se não existir app core):

```python
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def _is_admin(user):
    return user.groups.filter(name__in=['Administrador', 'administrador']).exists()

def glot_permission_required(modulo, acao):
    """
    Decorator para FBV.
    Uso: @glot_permission_required('vendas', 'ver')
    """
    perm = f'auth.glot_{modulo}_{acao}'

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if _is_admin(request.user) or request.user.has_perm(perm):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect('login')
        return wrapper
    return decorator


class GlotPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin para CBV.
    Uso: class MinhaView(GlotPermissionMixin, View):
             glot_modulo = 'vendas'
             glot_acao = 'ver'
    """
    glot_modulo = None
    glot_acao = None

    def get_permission_required(self):
        if self.glot_modulo and self.glot_acao:
            return [f'auth.glot_{self.glot_modulo}_{self.glot_acao}']
        return []

    def has_permission(self):
        if _is_admin(self.request.user):
            return True
        return super().has_permission()

    def handle_no_permission(self):
        messages.error(self.request, 'Você não tem permissão para acessar esta página.')
        return redirect('login')
```

---

## Passo 3 — Aplicar proteção por app

### Mapeamento de módulos

```
vendas/          → modulo='vendas'
clientes/        → modulo='clientes'
empreendimentos/ → modulo='empreendimentos'
documentos/      → modulo='documentos'
usuarios/        → modulo='usuarios'
relatorios/      → modulo='relatorios'
```

### FBV

```python
# Antes
@login_required
def lista_vendas(request): ...

# Depois
@glot_permission_required('vendas', 'ver')
def lista_vendas(request): ...
```

### CBV

```python
# Antes
class CriarVendaView(LoginRequiredMixin, CreateView): ...

# Depois
class CriarVendaView(GlotPermissionMixin, CreateView):
    glot_modulo = 'vendas'
    glot_acao = 'criar'
```

### Tabela de mapeamento

| Padrão de nome da view               | Ação               |
|--------------------------------------|--------------------|
| lista*, listar*, index               | ver                |
| detalhe*, detail*, get*              | ver                |
| criar*, novo*, new*, create*         | criar              |
| editar*, edit*, update*, atualizar*  | editar             |
| excluir*, deletar*, delete*, remover*| excluir            |
| relatorio*, exportar*, export*, pdf* | ver (relatorios)   |
| aprovar*, reprovar*, status*         | editar             |

### Ordem de execução (do mais crítico ao menos)

1. `vendas/`
2. `documentos/`
3. `clientes/`
4. `empreendimentos/`
5. `usuarios/`
6. Demais apps

---

## Passo 4 — Proteger templates (esconder botões)

```html
{% if perms.auth.glot_vendas_criar %}
  <a href="{% url 'criar_venda' %}">Nova Venda</a>
{% endif %}

{% if perms.auth.glot_vendas_editar %}
  <a href="{% url 'editar_venda' venda.pk %}">Editar</a>
{% endif %}

{% if perms.auth.glot_vendas_excluir %}
  <button>Excluir</button>
{% endif %}
```

Aplicar nos templates de lista, detalhe e cards de cada módulo.

---

## Passo 5 — Impersonate (acessar como outro usuário)

### Views em `usuarios/views.py`

```python
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

@login_required
def impersonate_start(request, pk):
    # Apenas Administrador pode impersonate
    if not request.user.groups.filter(name__in=['Administrador', 'administrador']).exists():
        messages.error(request, 'Sem permissão.')
        return redirect('lista_usuarios')

    # Não permitir impersonate de si mesmo
    if request.user.pk == pk:
        messages.warning(request, 'Você não pode acessar como você mesmo.')
        return redirect('detalhe_usuario', pk=pk)

    target = get_object_or_404(User, pk=pk)
    request.session['impersonator_id'] = request.user.id
    login(request, target, backend='django.contrib.auth.backends.ModelBackend')
    messages.info(request, f'Você está acessando como {target.get_full_name() or target.username}.')
    return redirect('home')  # ajustar para a home real do GLOT


@login_required
def impersonate_stop(request):
    impersonator_id = request.session.get('impersonator_id')
    if not impersonator_id:
        return redirect('home')

    original = get_object_or_404(User, pk=impersonator_id)
    del request.session['impersonator_id']
    login(request, original, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Você voltou à sua conta.')
    return redirect('lista_usuarios')
```

### URLs em `usuarios/urls.py`

```python
path('usuarios/<int:pk>/impersonate/', views.impersonate_start, name='impersonate_start'),
path('usuarios/impersonate/stop/', views.impersonate_stop, name='impersonate_stop'),
```

### Banner no `base.html`

Adicionar logo abaixo do `<body>` ou do navbar, visível apenas quando
`request.session.impersonator_id` estiver definido:

```html
{% if request.session.impersonator_id %}
<div class="bg-amber-400 text-amber-900 px-4 py-2 flex items-center justify-between text-sm font-medium sticky top-0 z-50">
  <span>
    ⚠️ Você está visualizando o sistema como
    <strong>{{ request.user.get_full_name|default:request.user.username }}</strong>
  </span>
  <a href="{% url 'impersonate_stop' %}"
     class="bg-amber-900 text-amber-100 px-3 py-1 rounded hover:bg-amber-800 transition">
    Voltar à minha conta
  </a>
</div>
{% endif %}
```

### Botão no detalhe do usuário

Adicionar no template de detalhe, visível apenas para Administrador
e apenas quando o usuário visualizado não é o próprio admin logado:

```html
{% if request.user.groups.all|filter_admin and request.user.pk != usuario.pk %}
  <a href="{% url 'impersonate_start' usuario.pk %}"
     class="...">
    Acessar como este usuário
  </a>
{% endif %}
```

Verificar como outras telas checam grupo Administrador no projeto
e usar o mesmo padrão.

---

## Regras gerais

- Substituir `@login_required` pelo decorator novo (não manter os dois)
- Views públicas NÃO proteger: login, logout, reset de senha
- Views de API/AJAX também devem ser protegidas
- `python manage.py check` → 0 erros após cada app
- Casos especiais (views com lógica de permissão própria): reportar antes de alterar

---

## Relatório final esperado

- Total de views protegidas por app
- Views que já tinham `@login_required` (substituídas)
- Views sem nenhuma proteção (adicionadas)
- Views públicas mantidas sem proteção
- Casos especiais encontrados
- Botões/links escondidos nos templates
- Resultado do `python manage.py check`
