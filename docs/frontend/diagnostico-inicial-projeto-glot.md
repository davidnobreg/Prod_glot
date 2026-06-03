# Primeira Análise Do Projeto GLOT

## 1. Resumo Do Projeto Encontrado

O GLOT é um monólito Django organizado por apps. O frontend atual é baseado principalmente em:

- Django Templates por app.
- Layout global em `base.html`.
- Bootstrap 5.3.3 carregado via CDN.
- Bootstrap Icons, Font Awesome, Select2, Flatpickr e jQuery.
- CSS próprio em `static/css/style.css`.
- Uma cópia parecida em `base/static/css/style.css`.
- Admin/Jazzmin/AdminLTE separados em `static/vendor/`, `static/jazzmin/`, `static/admin/`.

Quase todos os templates reais do sistema estendem `base.html`, então herdam Bootstrap automaticamente.

Não alterei nenhum arquivo durante a análise inicial.

---

## 2. Pastas Principais Identificadas

Apps com templates:

- `accounts/templates/` - login, usuários, reset.
- `base/templates/` - layout global, navbar, mensagens, rodapé, erros.
- `clientes/templates/` - cadastro, edição, lista, relatórios.
- `dashboard/templates/` - dashboard.
- `documentos/templates/` - contrato/documentos.
- `empreendimentos/templates/` - empreendimentos, quadras, lotes, reservas, relatórios.
- `vendas/templates/` - vendas, reservas, análise, propostas, relatórios.

Static:

- `static/css/`
- `static/js/`
- `static/scss/`
- `static/vendor/`
- `static/admin/`
- `static/jazzmin/`
- `base/static/css/`
- `base/static/js/`
- `base/static/scss/`

Observação: há duplicação entre `static/` e `base/static/`, principalmente CSS/JS. Antes de migrar visualmente, vale mapear qual pasta está sendo servida de fato em produção.

---

## 3. Templates Que Usam Bootstrap

Uso direto/global:

- `base/templates/base.html` carrega Bootstrap CSS/JS via CDN.
- `base/templates/navbar.html` usa navbar, dropdowns e botões Bootstrap.
- `base/templates/message.html` usa alerts/mensagens.

Como quase todos os templates estendem `base.html`, os principais templates Bootstrap são:

- `accounts/templates/lista_usuarios.html`
- `accounts/templates/login.html`
- `clientes/templates/cliente.html`
- `clientes/templates/cliente_update.html`
- `clientes/templates/lista_cliente.html`
- `clientes/templates/lista_cliente_relatorio.html`
- `empreendimentos/templates/lista-empreendimentos-tabela.html`
- `empreendimentos/templates/lista-quadras.html`
- `empreendimentos/templates/detalhes-do-empreendimento.html`
- `empreendimentos/templates/detalhes-reserva-lote.html`
- `empreendimentos/templates/relatorio_de_reservas_temporario.html`
- `vendas/templates/analisa.html`
- `vendas/templates/reserva.html`
- `vendas/templates/reservado.html`
- `vendas/templates/reservado_detalhe.html`
- `vendas/templates/lista_reserva.html`
- `vendas/templates/lista_venda.html`
- `vendas/templates/detalhe_reserva.html`

Mais acoplados ao Bootstrap por volume de classes:

- `vendas/templates/analisa.html`
- `vendas/templates/reserva.html`
- `clientes/templates/cliente.html`
- `vendas/templates/reservado.html`
- `clientes/templates/cliente_update.html`
- `empreendimentos/templates/lista-quadras.html`
- `empreendimentos/templates/detalhes-reserva-lote.html`
- `empreendimentos/templates/lista-empreendimentos-tabela.html`

---

## 4. Componentes Bootstrap Mais Usados

Classes mais frequentes encontradas:

| Classe | Ocorrências |
|---|---:|
| `btn` | 214 |
| `text-center` | 181 |
| `row` | 127 |
| `col-md-6` | 87 |
| `form-label` | 87 |
| `mb-3` | 74 |
| `mb-0` | 72 |
| `w-100` | 69 |
| `alert` | 65 |
| `btn-primary` | 63 |
| `btn-danger` | 54 |
| `d-flex` | 48 |
| `card` | 44 |
| `rounded-pill` | 42 |
| `col-md-4` | 38 |
| `container` | 35 |
| `btn-secondary` | 35 |
| `btn-success` | 34 |
| `form-control` | 29 |
| `modal` | 23 |
| `badge` | 23 |
| `table-responsive` | 16 |
| `table` | 15 |
| `table-striped` | 11 |

Componentes mais presentes:

- Botões: `btn`, `btn-primary`, `btn-danger`, `btn-success`, `btn-secondary`, `btn-warning`.
- Grid: `container`, `container-fluid`, `row`, `col-md-*`, `col-lg-*`, `col-12`, `col-6`.
- Formulários: `form-control`, `form-label`, `form-select`, `form-check`.
- Cards: `card`, `card-body`, `card-header`, `card-title`.
- Tabelas: `table`, `table-responsive`, `table-striped`, `table-hover`, `table-dark`.
- Modais: `modal`, `modal-dialog`, `modal-content`, `modal-header`, `modal-body`, `modal-footer`.
- Alertas/badges: `alert`, `alert-danger`, `alert-success`, `badge`.

---

## 5. Telas Recomendadas Para Começar

Começar por telas pequenas, com pouco risco operacional e pouco JS:

1. Páginas de erro:

- `base/templates/403.html`
- `base/templates/500.html`
- `base/templates/not_found.html`

2. Páginas simples de permissão:

- `empreendimentos/templates/permissao.html`
- `vendas/templates/permissaoVenda.html`

3. Dashboard simples:

- `dashboard/templates/dash.html`

4. Telas pequenas de formulário/visualização:

- `accounts/templates/reset.html`
- `accounts/templates/usuario.html`
- `accounts/templates/update_usuario.html`
- `vendas/templates/update_reserva.html`
- `clientes/templates/delete_cliente.html`

5. Relatórios simples:

- `clientes/templates/relatorio.html`
- `clientes/templates/lista_cliente_relatorio.html`
- `vendas/templates/lista_venda_relatorio.html`

Essas telas são melhores para validar a estratégia Tailwind sem mexer nos fluxos centrais.

---

## 6. Telas Que Devem Ficar Para Depois

Evitar no começo:

- `vendas/templates/reserva.html`
- `vendas/templates/analisa.html`
- `vendas/templates/reservado.html`
- `vendas/templates/reservado_detalhe.html`
- `clientes/templates/cliente.html`
- `clientes/templates/cliente_update.html`
- `empreendimentos/templates/lista-empreendimentos-tabela.html`
- `empreendimentos/templates/lista-quadras.html`
- `empreendimentos/templates/detalhes-reserva-lote.html`
- `vendas/templates/lista_reserva.html`
- `vendas/templates/lista_venda.html`

Motivos:

- Muitas classes Bootstrap.
- Muitos modais.
- Muitos formulários.
- Tabelas com ações.
- Fluxos críticos de reserva, venda, cliente e empreendimento.
- Maior chance de quebrar comportamento visual ou JS.

---

## 7. Plano Gradual De Migração

1. Não remover Bootstrap agora.

Manter Bootstrap ativo no `base.html`. Tailwind deve entrar em paralelo, não substituindo tudo de uma vez.

2. Criar camada visual própria.

Antes de migrar página por página, definir padrões equivalentes:

- Botões.
- Cards.
- Inputs.
- Tabelas.
- Alerts.
- Badges.
- Modais.

3. Migrar templates pequenos primeiro.

- Páginas de erro.
- Permissões.
- Dashboard.
- Telas sem tabela complexa.

4. Migrar componentes compartilhados com cuidado.

- `message.html` pode virar um bom primeiro componente compartilhado.
- `navbar.html` deve ficar para uma segunda fase, porque afeta o sistema inteiro.
- `base.html` não deve ser alterado agressivamente no início.

5. Migrar formulários simples.

- `reset.html`, `usuario.html`, `update_usuario.html`.
- Depois formulários médios de empreendimento/cliente.

6. Migrar tabelas simples.

- Relatórios e listagens com menos ações.
- Validar responsividade e paginação.

7. Migrar fluxos críticos por último.

- Reserva.
- Venda.
- Análise.
- Cliente completo.
- Empreendimento completo.

8. Só remover Bootstrap quando não houver dependência real.

- Modais Bootstrap precisam de JS Bootstrap.
- Navbar/dropdowns usam JS Bootstrap.
- Select2 e Flatpickr têm estilos próprios.
- Admin/Jazzmin/AdminLTE devem ficar separados da migração pública.

---

## 8. Próximo Passo Recomendado

Fazer um inventário mais preciso por template antes de qualquer alteração:

1. Separar templates em `baixo`, `médio` e `alto risco`.
2. Definir um padrão visual Tailwind equivalente ao visual atual: azul institucional `rgb(3, 107, 145)`, cards arredondados, fundo claro, botões pill.
3. Escolher uma primeira tela piloto simples, recomendação: `base/templates/not_found.html` ou `dashboard/templates/dash.html`.
4. Só depois criar a estrutura Tailwind em paralelo, sem remover Bootstrap.
