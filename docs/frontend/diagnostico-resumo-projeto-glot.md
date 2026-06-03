# Resumo Do Projeto Encontrado

O GLOT é um sistema monolítico desenvolvido em Django, organizado por apps modulares.

O frontend atual é baseado principalmente em:

- Django Templates organizados por app.
- Layout global centralizado em `base/templates/base.html`.
- Bootstrap 5.3.3 carregado via CDN.
- Bootstrap Icons carregado via CDN.
- Font Awesome carregado via CDN.
- Select2 carregado via CDN.
- Flatpickr carregado via CDN.
- jQuery carregado via CDN.
- CSS próprio em `static/css/style.css`.
- Cópia semelhante de CSS/JS em `base/static/`.

A maior parte das telas do sistema estende `base.html`, então herda automaticamente o Bootstrap, os scripts globais e o CSS customizado.

## Estrutura Visual Atual

O projeto usa uma combinação de:

- Bootstrap para grid, botões, cards, tabelas, modais, formulários e alertas.
- CSS customizado para identidade visual, principalmente gradientes, navbar, dashboard e impressão.
- Admin/Jazzmin/AdminLTE separados dos templates principais.
- Select2 para campos de seleção.
- Flatpickr para campos de data.
- jQuery e scripts próprios para máscaras e comportamentos de formulário.

## Características Do Frontend

A interface atual tem forte dependência de Bootstrap, principalmente nas seguintes classes:

- `btn`
- `row`
- `col-*`
- `container`
- `card`
- `form-control`
- `form-label`
- `table`
- `modal`
- `alert`
- `badge`

A identidade visual atual usa bastante:

- Fundo claro.
- Azul institucional próximo de `rgb(3, 107, 145)`.
- Botões arredondados.
- Cards com bordas arredondadas.
- Gradientes em navbar, cards e botões.
- Layouts com tabelas administrativas.
- Modais para ações e confirmações.

## Observações Importantes

Existe uma duplicação relevante entre:

- `static/`
- `base/static/`

Principalmente em arquivos CSS e JS.

Antes de qualquer migração visual, é recomendável confirmar qual pasta está sendo usada efetivamente em produção e evitar alterar arquivos duplicados sem entender o fluxo de `STATICFILES_DIRS` / `collectstatic`.

## Diagnóstico Inicial

O projeto está pronto para uma migração gradual para Tailwind CSS, mas não deve ter Bootstrap removido no início.

A melhor estratégia é usar Tailwind em paralelo, começando por telas simples e não críticas.

As telas mais críticas, como reserva, venda, análise, cliente e empreendimento, devem ficar para fases posteriores porque possuem muitos componentes Bootstrap, modais, tabelas, formulários e regras visuais já consolidadas.

## Conclusão

O frontend do GLOT é altamente acoplado ao Bootstrap, mas a estrutura baseada em templates Django permite uma migração incremental segura.

A migração ideal deve preservar:

- A identidade visual atual.
- O layout administrativo claro.
- O azul institucional.
- A organização por apps.
- O funcionamento dos modais, formulários, tabelas e scripts existentes.

Bootstrap deve permanecer ativo até que cada tela ou componente tenha sido migrado e validado individualmente.
