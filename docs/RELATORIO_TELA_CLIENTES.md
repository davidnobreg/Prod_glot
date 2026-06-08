# Relatorio — Tela de Clientes (Cadastro e Listagem)

Data: 2026-06-08

## Objetivo

Modernizar a tela de **cadastro** (`cliente.html`) e a **listagem** (`lista_cliente.html`) com foco em:

- organizacao visual do formulario (secoes e alinhamento);
- botoes padronizados e com hierarquia clara;
- regra de exibicao do conjuge via **Estado civil**;
- listagem mais profissional, com status e melhor UX em mobile;
- manter o padrao visual do sistema (sidebar/cores/base).

## Principais problemas encontrados (antes)

- `cliente.html` e `cliente_update.html` tinham JS inline duplicado para mostrar/ocultar conjuge.
- O cadastro dependia de valores de contexto (`origem`, `lote_uuid`) mas esses inputs/hidden fields podiam nao ser enviados dependendo de como o template renderizava o form.
- `telefone.js` era acoplado a classes Bootstrap (`list-group-item`, `btn-outline-danger`) e usava um id de modal errado (`modalTelefone`), o que dificultava modernizacao e consistencia visual.
- A listagem tinha acoes com `data-bs-toggle` duplicado (modal + tooltip no mesmo elemento), o que conflita no Bootstrap.

## O que foi alterado

### 1) Cadastro de cliente — `clientes/templates/cliente.html`

- Reescrita completa do layout com seções logicas:
  - Dados pessoais
  - Documentos
  - Contato
  - Endereco
  - Dados conjugais (condicional)
  - Observacoes
- Criado header com acoes claras (Voltar / Salvar) e barra de acoes ao final (Adicionar telefone / Limpar / Cancelar / Salvar).
- Modal de telefones ganhou estrutura consistente com Tailwind e lista renderizada pelo JS (sem depender de classes Bootstrap antigas).
- Inputs hidden para fluxo de reserva foram garantidos:
  - `origem`
  - `lote_uuid` (quando existe)
  - `telefones_json`

### 2) Edicao de cliente — `clientes/templates/cliente_update.html`

- Ajustado para seguir o mesmo padrao visual do cadastro.
- Garantidos `origem`, `lote_uuid` e `telefones_json` no POST.

### 3) Regra Estado Civil -> Conjuge — `static/js/cliente.js`

- Removida logica antiga ligada a `conjugeForm`/`conjugeModal` (nao existiam na UI atual).
- Implementada uma unica logica robusta:
  - Se `estado_civil == "casado"`: exibe `#secaoConjuge`, habilita campos e marca `conj_nome` como required.
  - Caso contrario: oculta a secao e desabilita os campos do conjuge (evita submit de valores quando oculto).
- Mantida compatibilidade com Select2 caso o campo vire select2 no futuro (escuta `select2:*` quando jQuery existir).

### 4) Telefones (modal) — `static/js/telefone.js`

- Reescrito para gerar a lista com classes Tailwind (`tw:`), evitando dependencia de `list-group-item`.
- Corrigido id do modal usado em `fecharModal` para `modalTelefones`.
- A lista funciona tanto no cadastro quanto na edicao, atualizando `#telefones_json`.

### 5) Listagem — `clientes/templates/lista_cliente.html`

- Refeito seguindo a refer�ncia de tabela moderna:
  - Topo com t�tulo + subt�tulo + bot�es principais.
  - Busca com �cone, fundo cinza claro e bordas arredondadas.
  - **Cards no mobile** e **tabela no desktop**.
  - Coluna principal com avatar (iniciais) + nome + documento.
  - Badges suaves:
    - `Ativo` (a view atual lista somente ativos)
    - `Cadastro completo` / `Pendente` (endere�o completo + telefones).
  - Rodap� com contagem "Mostrando X a Y de Z" e pagina��o centralizada.

Obs.: a��es como "Visualizar" / "Ver contratos" n�o foram adicionadas porque n�o existe endpoint dedicado no m�dulo de clientes hoje. O padr�o visual (toolbar/table/actions) foi estruturado para receber essas a��es quando existirem.

### 6) Padronizacao visual via Tailwind Components — `base/static/css/tailwind.input.css`

- Criadas classes de componentes para reduzir repeticao e melhorar manutencao:
  - `glot-card`, `glot-card-body`
  - `glot-input`, `glot-select`, `glot-textarea`
  - `glot-btn-*` e `glot-icon-btn-*`
  - `glot-badge-*`
- Criado um padr�o reaproveit�vel para listagens:
  - `glot-page`, `glot-page-header`, `glot-toolbar`
  - `glot-search-*`
  - `glot-table-*` / `glot-footer` / `glot-pagination`
- Adicionado `@source "../../../**/*.js";` para Tailwind enxergar classes usadas em JS (ex.: lista de telefones).
- CSS recompilado via `npm run build:css`.

### 7) Widgets/Forms — `clientes/forms.py`

- Adicionadas helpers `_merge_classes` e `_apply_widget_style` para aplicar as classes padrao (`glot-*`) em inputs/selects/textarea.
- Mantidas classes de mascara (`mask-doc`, `mask-phone`, etc.) e ids usados pelos scripts.
- O objetivo foi deixar os campos com aparencia moderna sem mexer na regra de negocio.

## Campos de conjuge que NAO existem no model hoje

O model `Cliente` possui apenas:

- `conj_nome`
- `conj_documento`
- `conj_numero_rg`
- `conj_orgao_emissor_rg`

O layout do `cliente.html` ja prepara a estrutura visual para:

- Telefone do conjuge
- E-mail do conjuge
- Profissao do conjuge
- Nacionalidade do conjuge
- Naturalidade do conjuge

Para persistir esses dados, seria necessario adicionar campos no model (exemplo):

- `conj_telefone`
- `conj_email`
- `conj_profissao`
- `conj_nacionalidade`
- `conj_naturalidade`

E depois refletir no `ClienteConjugeForm`/views/migrations.

## Pontos que ainda podem ser melhorados (proximos passos)

- Listar tambem clientes inativos (ou criar filtro Ativo/Inativo) — hoje a view filtra `is_ativo=True`.
- Criar pagina de visualizacao (detalhe) do cliente (nao existe endpoint dedicado; hoje so existe update/delete/list).
- Revisar a regra de obrigatoriedade do CPF do conjuge no backend:
  - atualmente o backend exige apenas `conj_nome` quando casado;
  - se a regra do negocio pedir CPF obrigatorio, deve ser validado no backend para nao depender apenas do frontend.
