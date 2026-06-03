# Plano Técnico De Migração Bootstrap Para Tailwind No GLOT

## 1. Objetivo Da Migração

Migrar gradualmente o frontend do GLOT de Bootstrap para Tailwind CSS, mantendo o sistema funcional durante todo o processo.

A migração deve preservar:

- Identidade visual atual.
- Experiência administrativa limpa.
- Responsividade.
- Legibilidade de tabelas.
- Fluxos críticos de venda, reserva, análise, cliente e empreendimento.
- Compatibilidade com Select2, Flatpickr, jQuery e scripts existentes.

Bootstrap deve continuar ativo até que todas as telas migradas estejam validadas e não dependam mais de componentes ou JS Bootstrap.

---

## 2. Estratégia Geral

A estratégia recomendada é **migração paralela e incremental**.

Não substituir Bootstrap globalmente no início.

Fluxo recomendado:

1. Manter Bootstrap no `base.html`.
2. Introduzir Tailwind em paralelo somente quando a estrutura estiver planejada.
3. Começar por telas simples e não críticas.
4. Criar padrões visuais equivalentes aos componentes Bootstrap atuais.
5. Migrar pequenos grupos de templates.
6. Testar visual e funcionalmente cada etapa.
7. Só remover Bootstrap quando não houver dependências reais.

Princípio principal:

> Primeiro reduzir risco. Depois ganhar consistência visual. Só no final remover dependências antigas.

---

## 3. Ordem Recomendada Das Etapas

### Etapa 0 — Inventário Técnico

Antes de instalar Tailwind:

- Confirmar qual pasta static é usada em produção:
  - `static/`
  - `base/static/`
- Confirmar `STATICFILES_DIRS`.
- Mapear arquivos CSS realmente carregados.
- Mapear scripts que dependem de Bootstrap JS.
- Identificar templates com:
  - modais Bootstrap
  - dropdowns Bootstrap
  - tabelas
  - forms complexos
  - Select2
  - Flatpickr

Resultado esperado:

- Lista de telas por risco: baixo, médio, alto.
- Lista de componentes Bootstrap ainda usados.
- Lista de arquivos estáticos ativos.

### Etapa 1 — Preparar Design Tokens

Definir tokens visuais equivalentes ao visual atual:

- Azul institucional: `rgb(3, 107, 145)`
- Azul escuro: variação para hover.
- Fundo geral claro: `#f5f7fb`
- Branco de cards: `#ffffff`
- Cinza de borda: `#e5e7eb`
- Texto principal: `#111827`
- Texto secundário: `#6b7280`
- Danger: vermelho próximo ao Bootstrap.
- Success: verde próximo ao Bootstrap.
- Warning: amarelo/laranja controlado.

Objetivo:

- Evitar que cada tela crie um visual diferente.
- Preservar a essência atual do sistema.

### Etapa 2 — Instalar Tailwind Em Paralelo

Somente após validação do inventário.

Regras:

- Não remover Bootstrap.
- Não alterar `base.html` diretamente no primeiro teste.
- Preferir criar CSS Tailwind separado.
- Usar escopo/estratégia que minimize conflito com Bootstrap.
- Validar build local antes de aplicar em templates reais.

### Etapa 3 — Criar Componentes Visuais Base

Criar classes utilitárias ou padrões reutilizáveis para:

- Botões.
- Cards.
- Alerts.
- Badges.
- Inputs.
- Selects.
- Tabelas.
- Containers.
- Estados vazios.
- Títulos de página.

Recomendação:

- Evitar copiar Bootstrap 1:1.
- Manter aparência próxima, mas com Tailwind.
- Priorizar consistência e legibilidade.

### Etapa 4 — Migrar Telas Piloto Baixo Risco

Começar por telas simples:

- `base/templates/403.html`
- `base/templates/500.html`
- `base/templates/not_found.html`
- `dashboard/templates/dash.html`
- `empreendimentos/templates/permissao.html`
- `vendas/templates/permissaoVenda.html`

Critério:

- Pouco JS.
- Pouco formulário.
- Pouca regra de negócio.
- Sem fluxo operacional crítico.

### Etapa 5 — Migrar Formulários Simples

Depois de validar os pilotos:

- `accounts/templates/reset.html`
- `accounts/templates/usuario.html`
- `accounts/templates/update_usuario.html`
- `vendas/templates/update_reserva.html`
- `clientes/templates/delete_cliente.html`

Atenção:

- Manter compatibilidade com `form-control` enquanto Bootstrap estiver ativo.
- Se o formulário depender de Select2/Flatpickr, testar visual e comportamento.

### Etapa 6 — Migrar Relatórios Simples E Tabelas Menores

Templates recomendados:

- `clientes/templates/relatorio.html`
- `clientes/templates/lista_cliente_relatorio.html`
- `vendas/templates/lista_venda_relatorio.html`

Critérios de validação:

- Tabelas responsivas.
- Paginação.
- Botões de ação.
- Filtros.
- Impressão, se aplicável.

### Etapa 7 — Migrar Componentes Compartilhados

Somente depois de várias telas piloto estarem estáveis:

- `base/templates/message.html`
- componentes de botões repetidos
- padrões de cards
- padrões de tabela

Evitar ainda:

- `base/templates/base.html`
- `base/templates/navbar.html`

Motivo:

- `base.html` afeta todas as telas.
- `navbar.html` depende de dropdown Bootstrap e impacta navegação global.

### Etapa 8 — Migrar Telas Médias

Migrar telas com complexidade média:

- `empreendimentos/templates/reserva-temporaria.html`
- `vendas/templates/reserva-temporaria-vendas.html`
- `empreendimentos/templates/update_empreendimento.html`
- `empreendimentos/templates/editar-atualizar-lote.html`
- `empreendimentos/templates/relatorio-financeiro.html`

Critério:

- Fazer uma tela por vez.
- Validar visual antes de avançar.

### Etapa 9 — Migrar Telas Críticas Por Último

Deixar para o final:

- Venda.
- Reserva.
- Análise.
- Cliente completo.
- Empreendimento completo.

Templates:

- `vendas/templates/reserva.html`
- `vendas/templates/analisa.html`
- `vendas/templates/reservado.html`
- `vendas/templates/reservado_detalhe.html`
- `vendas/templates/lista_reserva.html`
- `vendas/templates/lista_venda.html`
- `clientes/templates/cliente.html`
- `clientes/templates/cliente_update.html`
- `empreendimentos/templates/lista-empreendimentos-tabela.html`
- `empreendimentos/templates/lista-quadras.html`
- `empreendimentos/templates/detalhes-reserva-lote.html`

---

## 4. Arquivos Que Devem Ser Evitados No Início

Evitar alterar no início:

- `base/templates/base.html`
- `base/templates/navbar.html`
- `vendas/templates/reserva.html`
- `vendas/templates/analisa.html`
- `vendas/templates/reservado.html`
- `vendas/templates/reservado_detalhe.html`
- `vendas/templates/lista_reserva.html`
- `vendas/templates/lista_venda.html`
- `clientes/templates/cliente.html`
- `clientes/templates/cliente_update.html`
- `empreendimentos/templates/lista-empreendimentos-tabela.html`
- `empreendimentos/templates/lista-quadras.html`
- `empreendimentos/templates/detalhes-reserva-lote.html`

Também evitar:

- `models.py`
- `views.py`
- `urls.py`
- migrations
- permissões
- settings de autenticação
- lógica de negócio
- scripts JS globais sem necessidade

---

## 5. Arquivos Que Podem Ser Usados Como Piloto

Ordem recomendada:

1. `base/templates/not_found.html`
2. `base/templates/403.html`
3. `base/templates/500.html`
4. `dashboard/templates/dash.html`
5. `empreendimentos/templates/permissao.html`
6. `vendas/templates/permissaoVenda.html`
7. `accounts/templates/reset.html`
8. `accounts/templates/usuario.html`
9. `clientes/templates/delete_cliente.html`

Motivo:

- São telas menores.
- Têm menor risco operacional.
- Ajudam a validar padrão visual.
- Permitem testar Tailwind sem mexer em fluxo financeiro/comercial.

---

## 6. Padrão Visual Tailwind Sugerido

### Botões

Base:

```html
class="inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
```

Primário:

```html
class="bg-[rgb(3,107,145)] text-white hover:bg-sky-800 focus:ring-sky-700"
```

Secundário:

```html
class="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
```

Danger:

```html
class="bg-red-600 text-white hover:bg-red-700 focus:ring-red-600"
```

Success:

```html
class="bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-600"
```

Warning:

```html
class="bg-amber-500 text-white hover:bg-amber-600 focus:ring-amber-500"
```

### Cards

```html
class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
```

Header de card:

```html
class="mb-4 border-b border-slate-200 pb-4"
```

Título:

```html
class="text-lg font-semibold text-slate-900"
```

Descrição:

```html
class="text-sm text-slate-500"
```

### Alerts

Base:

```html
class="rounded-xl border px-4 py-3 text-sm"
```

Success:

```html
class="border-emerald-200 bg-emerald-50 text-emerald-800"
```

Danger:

```html
class="border-red-200 bg-red-50 text-red-800"
```

Warning:

```html
class="border-amber-200 bg-amber-50 text-amber-800"
```

Info:

```html
class="border-sky-200 bg-sky-50 text-sky-800"
```

### Badges

Base:

```html
class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold"
```

Primary:

```html
class="bg-sky-100 text-sky-800"
```

Success:

```html
class="bg-emerald-100 text-emerald-800"
```

Danger:

```html
class="bg-red-100 text-red-800"
```

Warning:

```html
class="bg-amber-100 text-amber-800"
```

Neutral:

```html
class="bg-slate-100 text-slate-700"
```

### Formulários

Label:

```html
class="mb-1 block text-sm font-medium text-slate-700"
```

Input:

```html
class="block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-[rgb(3,107,145)] focus:outline-none focus:ring-2 focus:ring-sky-100"
```

Select:

```html
class="block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-[rgb(3,107,145)] focus:outline-none focus:ring-2 focus:ring-sky-100"
```

Help text:

```html
class="mt-1 text-xs text-slate-500"
```

Erro:

```html
class="mt-1 text-xs font-medium text-red-600"
```

### Tabelas

Wrapper responsivo:

```html
class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
```

Scroll horizontal:

```html
class="overflow-x-auto"
```

Tabela:

```html
class="min-w-full divide-y divide-slate-200 text-sm"
```

Thead:

```html
class="bg-slate-50"
```

Th:

```html
class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
```

Td:

```html
class="px-4 py-3 text-slate-700"
```

Linha hover:

```html
class="hover:bg-slate-50"
```

Ação em tabela:

```html
class="inline-flex items-center rounded-full px-3 py-1.5 text-xs font-semibold"
```

---

## 7. Riscos Da Migração

Principais riscos:

- Conflito visual entre Bootstrap e Tailwind.
- Reset/preflight do Tailwind afetar Bootstrap.
- Modais Bootstrap deixarem de funcionar se Bootstrap JS for removido cedo.
- Dropdown da navbar quebrar.
- Select2 perder alinhamento visual.
- Flatpickr ficar visualmente inconsistente.
- Tabelas grandes perderem responsividade.
- Impressão de documentos/relatórios quebrar.
- Duplicação `static/` e `base/static/` gerar alterações no arquivo errado.
- Alterações em `base.html` afetarem todas as telas.
- Mistura prolongada de classes Bootstrap e Tailwind dificultar manutenção.

Mitigações:

- Não remover Bootstrap no início.
- Não alterar `base.html` primeiro.
- Migrar uma tela por vez.
- Validar em desktop e mobile.
- Criar checklist visual.
- Manter rollback simples por commit pequeno.
- Evitar mexer em JS global junto com visual.
- Separar migração de CSS de migração de comportamento.

---

## 8. Como Testar Cada Etapa

Checklist mínimo por tela:

- Página carrega sem erro.
- Layout desktop correto.
- Layout mobile correto.
- Navbar continua funcionando.
- Dropdowns continuam funcionando.
- Botões mantêm ação correta.
- Forms enviam corretamente.
- Validações aparecem corretamente.
- Mensagens aparecem corretamente.
- Modais abrem e fecham, se existirem.
- Select2 funciona, se existir.
- Flatpickr funciona, se existir.
- Tabelas não estouram largura.
- Paginação funciona, se existir.
- Impressão funciona, se existir.
- Console do navegador sem erro JS novo.

Checklist Django:

- Rodar servidor local.
- Acessar tela manualmente.
- Testar fluxo principal da tela.
- Testar permissões visuais.
- Confirmar que nenhuma view/model/url foi alterada.
- Se houver testes existentes, rodar pytest.

Checklist visual:

- Fundo claro preservado.
- Azul institucional preservado.
- Botões arredondados.
- Cards arredondados.
- Tabelas legíveis.
- Espaçamento consistente.
- Responsividade aceitável.

---

## 9. Quando Será Seguro Remover Bootstrap

Só será seguro remover Bootstrap quando todos os critérios abaixo forem verdadeiros:

- Nenhum template público usa classes Bootstrap essenciais.
- Nenhum componente depende de Bootstrap JS.
- Navbar/dropdowns foram migrados para Tailwind ou JS próprio.
- Modais foram migrados para solução própria ou biblioteca compatível.
- Alerts, badges, forms, cards e tabelas já têm padrão Tailwind.
- Select2 e Flatpickr estão estilizados independentemente.
- Admin/Jazzmin/AdminLTE não dependem do Bootstrap público carregado no `base.html`.
- Impressão de contratos/relatórios foi validada.
- Todas as telas críticas foram testadas manualmente.
- O sistema foi testado em desktop e mobile.
- Existe rollback simples.

Importante:

Bootstrap usado por Admin/Jazzmin/AdminLTE não deve ser confundido com Bootstrap do frontend público do sistema. A remoção deve atingir apenas o frontend do `base.html`, não o admin.

---

## 10. Próximo Prompt Recomendado

```markdown
# Inventário técnico antes de instalar Tailwind no GLOT

Analise o projeto GLOT sem alterar arquivos.

Objetivo:
Mapear exatamente quais arquivos estáticos e templates precisam ser considerados antes de instalar Tailwind.

Regras:
1. Não altere arquivos.
2. Não instale dependências.
3. Não remova Bootstrap.
4. Não altere base.html.
5. Apenas analise.

Entregue:
1. Configuração Django relacionada a static files.
2. Qual `style.css` parece ser carregado de fato.
3. Templates que estendem `base.html`.
4. Templates com maior dependência de Bootstrap.
5. Templates com modais Bootstrap.
6. Templates com tabelas Bootstrap.
7. Templates com formulários complexos.
8. Scripts JS globais carregados.
9. Riscos antes da instalação do Tailwind.
10. Recomendação objetiva para a primeira tela piloto.
```
