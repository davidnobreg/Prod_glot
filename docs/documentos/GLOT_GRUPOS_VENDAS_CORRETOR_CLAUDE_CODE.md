# GLOT — Fase 2 Complemento + Vendas do Corretor

## Contexto

A Fase 2 entregou lista, criar e editar grupos. Faltou a associação de usuários
a grupos. Este prompt implementa isso junto com a seção de vendas no detalhe
do usuário.

---

## Parte 1 — Associar Usuários a Grupos

### URL — adicionar em `usuarios/urls.py`

```python
path('usuarios/<int:pk>/grupos/', views.associar_grupos, name='associar_grupos'),
```

### View `associar_grupos` em `usuarios/views.py`

- GET: carrega usuário + grupos disponíveis + grupos atuais do usuário
- POST: recebe lista `grupos[]` com IDs, faz `user.groups.set(grupos_selecionados)`
- Protegida com `@login_required` + verificação de grupo `Administrador`
- Redireciona para detalhe do usuário após salvar com mensagem de sucesso

```python
def associar_grupos(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    todos_grupos = Group.objects.all().order_by('name')
    
    if request.method == 'POST':
        grupo_ids = request.POST.getlist('grupos')
        grupos = Group.objects.filter(id__in=grupo_ids)
        usuario.groups.set(grupos)
        messages.success(request, f'Grupos de {usuario.get_full_name()} atualizados.')
        return redirect('detalhe_usuario', pk=pk)
    
    context = {
        'usuario': usuario,
        'todos_grupos': todos_grupos,
        'grupos_atuais': usuario.groups.values_list('id', flat=True),
    }
    return render(request, 'usuarios/associar_grupos.html', context)
```

### Template `usuarios/templates/usuarios/associar_grupos.html`

Padrão Tailwind. Layout simples:

- Título: "Grupos de Acesso — {nome do usuário}"
- Lista de checkboxes, um por grupo disponível
- Grupos já associados aparecem marcados
- Mostrar quantos usuários cada grupo já tem (excluindo o atual)
- Botão Salvar e Cancelar (volta para detalhe do usuário)

```
Grupos disponíveis:

[ ] Administrador  (2 usuários)
[x] Corretor       (5 usuários)
[ ] Proprietario   (3 usuários)
[ ] Financeiro     (1 usuário)

[Salvar]  [Cancelar]
```

### Botão no detalhe do usuário

Localizar o template de detalhe do usuário e adicionar botão:

```html
{% if request.user|is_administrador %}
  <a href="{% url 'associar_grupos' usuario.pk %}">
    Gerenciar Grupos
  </a>
{% endif %}
```

Usar a verificação de grupo que já existe no projeto (verificar como outras
telas fazem — pode ser templatetag, context processor ou check direto).

---

## Parte 2 — Vendas do Corretor no Detalhe do Usuário

### Atualizar a view de detalhe do usuário

Verificar em `vendas/models.py` → `RegisterVenda` qual campo vincula o corretor
(pode ser `corretor`, `usuario`, `vendedor` ou similar — verificar antes de implementar).

Adicionar ao contexto da view:

```python
from django.contrib.auth.models import Group
from vendas.models import RegisterVenda
from empreendimentos.models import Empreendimento
from django.db.models import Sum, Count

def detalhe_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    
    eh_corretor = usuario.groups.filter(name='Corretor').exists()
    vendas = None
    totais = {}
    
    if eh_corretor:
        vendas = RegisterVenda.objects.filter(
            <campo_corretor>=usuario  # usar nome real do campo
        ).select_related(
            'lote', 'lote__empreendimento', 'cliente'
        ).order_by('-data_venda')
        
        # Filtros via GET
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        empreendimento_id = request.GET.get('empreendimento')
        
        if data_inicio:
            vendas = vendas.filter(data_venda__gte=data_inicio)
        if data_fim:
            vendas = vendas.filter(data_venda__lte=data_fim)
        if empreendimento_id:
            vendas = vendas.filter(lote__empreendimento_id=empreendimento_id)
        
        totais = vendas.aggregate(qtd=Count('id'), valor_total=Sum('valor_total'))
    
    context = {
        # ...contexto existente, não remover nada...
        'eh_corretor': eh_corretor,
        'vendas': vendas,
        'totais': totais,
        'empreendimentos': Empreendimento.objects.filter(ativo=True),
    }
```

### Seção no template de detalhe do usuário

Adicionar **abaixo** das informações do usuário, só se `eh_corretor`:

#### Cards de totais
```
┌──────────────────┐  ┌──────────────────┐
│  Total de Vendas  │  │   Valor Total    │
│        12         │  │  R$ 480.000,00   │
└──────────────────┘  └──────────────────┘
```

#### Filtros (GET — preservar na paginação)
```
[Data início] [Data fim] [Empreendimento ▾] [Filtrar] [Limpar]
```

#### Tabela de vendas
```
| Nº   | Cliente       | Empreendimento  | Lote | Valor         | Data       | Status   | Ação |
|------|---------------|-----------------|------|---------------|------------|----------|------|
| #042 | João da Silva | Solar das Artes | L-12 | R$ 45.000,00  | 10/06/2026 | Contrato | Ver  |
```

- "Ver" → link para `/vendas/<id>/`
- Status com badge colorido (padrão existente no GLOT)
- Paginação: 10 itens por página preservando parâmetros GET
- Sem vendas: "Nenhuma venda encontrada para os filtros selecionados."

---

## Regras gerais

- Seção de vendas só aparece para usuários do grupo `Corretor`
- Totais refletem o resultado filtrado
- Não alterar models
- Não quebrar telas existentes
- Padrão visual Tailwind em todos os templates

---

## Como testar

**Associar grupos:**
1. Acessar detalhe de qualquer usuário como Administrador — botão "Gerenciar Grupos" deve aparecer
2. Acessar `/usuarios/<id>/grupos/` — checkboxes com grupos atuais marcados
3. Alterar grupos e salvar — verificar com `user.groups.all()` no shell
4. Acessar como Corretor — botão não deve aparecer

**Vendas do corretor:**
1. Usuário sem grupo Corretor — seção não aparece
2. Corretor sem vendas — seção aparece com mensagem vazia
3. Corretor com vendas — listar corretamente com totais
4. Filtrar por empreendimento e período — totais atualizam
5. Paginar — parâmetros GET preservados na URL

---

## Arquivos esperados ao final

- `usuarios/urls.py` — 1 nova rota
- `usuarios/views.py` — view `associar_grupos` + detalhe atualizado
- `usuarios/templates/usuarios/associar_grupos.html`
- Template detalhe do usuário — botão "Gerenciar Grupos" + seção de vendas
