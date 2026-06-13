# GLOT — Modernizar listar_analise.html

## Contexto

Modernizar a tela `/vendas/listar_analise/` mantendo toda a lógica existente.
Referência visual: cards com fundo escuro gradiente azul/teal, label pequeno
acima do valor em destaque (padrão já usado no resumo financeiro do projeto).

---

## Filtros — uma única linha

Reescrever a área de filtros em um card compacto com todos os campos em uma
única linha horizontal:

```
[Busca...] [Empreendimento ▾] [Status ▾] [Corretor ▾] [Data início] [Data fim] [Filtrar] [Limpar]
```

- Inputs com `h-9` ou `h-10`, compactos
- Botão **Filtrar**: azul/teal sólido
- Botão **Limpar**: outline cinza
- Em telas menores: quebrar em 2 linhas com `flex-wrap`
- Preservar todos os parâmetros GET existentes — não alterar a view

---

## Lista — trocar tabela por cards

Substituir a tabela atual por grid de cards no estilo da imagem enviada.

### Layout do grid
```
grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4
```

### Visual do card

Fundo com gradiente escuro azul/teal (igual ao resumo financeiro):
```css
background: linear-gradient(135deg, #0f3460 0%, #16637a 100%);
```

Estrutura interna do card:
```
┌─────────────────────────────────────────────────┐
│  #0042                          [badge status]  │
│                                                 │
│  Cliente          Lote                          │
│  João da Silva    L-12 · Solar das Artes        │
│                                                 │
│  Valor total      Parcelas                      │
│  R$ 48.419,36     180x · R$ 269,00              │
│                                                 │
│  Corretor         Data                          │
│  Carlos Lima      10/06/2026                    │
│                                                 │
│  ─────────────────────────────────────────────  │
│  [Ver detalhes →]                    [Aprovar]  │
└─────────────────────────────────────────────────┘
```

### Detalhes visuais
- Número da venda: `text-xs text-white/60` no topo esquerdo
- Badge de status: canto superior direito, colorido conforme padrão GLOT
- Labels (Cliente, Lote, etc.): `text-xs font-medium text-white/60 uppercase tracking-wide`
- Valores: `text-sm font-semibold text-white`
- Valor total: `text-lg font-bold text-yellow-400` (destaque como na imagem)
- Divisor: `border-t border-white/10`
- Botão "Ver detalhes": link texto `text-white/80 hover:text-white text-sm`
- Botão "Aprovar" (se existir na tela atual): `bg-white/20 hover:bg-white/30 text-white text-xs px-3 py-1 rounded`
- Corretor `None`: exibir `"-"` (proteção já identificada anteriormente)

### Cards de totais (topo da página)

Manter os cards de totais existentes, estilizar no mesmo padrão escuro:
- Total de vendas em análise
- Valor total em análise

---

## Empty state

Quando não há resultados:
```
[ícone] Nenhuma venda em análise encontrada
        Tente ajustar os filtros acima.
```

---

## Paginação

Manter paginação existente, estilizar em Tailwind preservando parâmetros GET.

---

## Regras

- Não alterar view, URL nem lógica Python
- Preservar todos os `{% url %}`, `{% if %}`, `{% for %}` existentes
- `python manage.py check` → 0 erros ao final
- Verificar template do resumo financeiro como referência do gradiente exato usado no projeto
