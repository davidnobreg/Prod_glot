# Módulo `empreendimentos`

> Relatório técnico completo. Gerado a partir da leitura de todo o código-fonte do app em 2026-07-13.

Mount point raiz: `path('empreendimentos/', include('empreendimentos.urls'))` (`core/urls.py:15`).

---

## 1. Visão geral

App responsável pelo cadastro de **empreendimentos** (loteamentos), sua estrutura de **quadras** e **lotes**, o ciclo de reserva/pré-reserva de lote, relatórios financeiros e de lotes (PDF/Excel), vínculo de corretores por empreendimento e vínculo de modelos de documento por empreendimento. É o módulo "raiz" do domínio — `vendas`, `documentos`, `accounts`, `dashboard` e `mensagem` dependem de `Empreendimento`/`Lote`, mas `empreendimentos` também importa de `vendas` (`RegisterVenda`) e `documentos` (`ModeloDocumento`, `EmpreendimentoDocumento`) — ver seção 11.

---

## 2. Models (`models.py`)

### `Empreendimento`
Cadastro do loteamento/empreendimento.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `uuid` | `UUIDField` | único, indexado — usado em todas as rotas |
| `nome` | `CharField(100)` | |
| `telefone` | `CharField(15)` | `RegexValidator` formato `(99) 99999-9999` |
| `tempo_reserva` | `IntegerField` | dias de validade da reserva (usado em `alteraLote`, `renovaReserva`, task `destravar_lotes_expirados`) |
| `quantidade_parcela` | `IntegerField` | usado em cálculo de parcela em várias views |
| `logo` | `ImageField` | upload em `empreendimentos/{uuid}/documentos/{filename}`, validado por `_validate_logo_arquivo` (só jpg/jpeg, max 10MB — **mensagem de erro cita "JPG ou PNG" mas só aceita jpg/jpeg**, ver §12) |
| `cnpj` | `CharField(18)` | único, nullable |
| `codBanco`, `banco`, `agencia`, `conta`, `razaoSocial` | dados bancários | `banco` usa choices `TypeBancos` |
| `rua`, `complemento`, `numero`, `bairro`, `cep`, `cidade`, `estado` | endereço | `estado` usa `choices_estado` (27 UFs), default `'PB'` |
| `observacao` | `TextField` | |
| `tipo_correcao` | `CharField(10)` | default `'IGPM'` |
| `desconto` | `CharField(2)` | default `'0'` |
| `is_ativo` | `BooleanField` | soft-delete |
| `representante_nome`, `representante_cpf`, `representante_rg`, `matricula`, `cidade_foro` | dados do representante legal + matrícula do imóvel, usados em documentos gerados |

`Meta`: `ordering = ['id']`. `__str__` retorna `nome`.

Choices auxiliares: `choices_estado` (tupla, 27 UFs), `TypeBancos` (`TextChoices`: Banco do Brasil, Banco do Nordeste, Caixa Econômica, Sicoob, Sicred).

### `Quadra`
| Campo | Tipo |
|---|---|
| `id` | `BigAutoField` |
| `namequadra` | `CharField(50)` |
| `empr` | `FK(Empreendimento, on_delete=CASCADE, related_name='empreendimento')` |

**Nota:** `related_name='empreendimento'` é um nome de related_name confuso (deveria ser algo como `quadras`) — não é usado em nenhum lugar do código (todo acesso reverso usa `empreendimento.empreendimento_set` implícito ou queries diretas `Quadra.objects.filter(empr=...)`), então o nome ruim não quebra nada, mas atrapalha legibilidade.

### `Lote`
| Campo | Tipo | Observação |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `uuid` | `UUIDField` | único |
| `lote` | `CharField(50)` | nome/número do lote |
| `area` | `CharField(50)` | **string, não decimal** — todo cálculo financeiro faz `float(lote.area)`/`Decimal(str(...))` na view |
| `situacao` | `CharField(100, choices=TypeLote)` | máquina de estados do lote |
| `tempo_reservado` | `DateTimeField` nullable | prazo da reserva `EM_RESERVA` |
| `quadra` | `FK(Quadra, CASCADE, related_name='lotes')` | |
| `valor_metro_quadrado` | `CharField(50)` | **também string**, default `00.00` (int, não string — inconsistência de tipo no default) |
| `cliente_reserva` | `CharField(100)` | default `0` (string) |
| `telefone`, `telefone_user` | `CharField(15)` | mesmo regex de telefone |
| `user` | `CharField(100)` | **não é FK pra `User`, é texto livre** (guarda `first_name` do corretor) |
| `data_termina_reserva` | `DateField` | default `datetime.now` |
| `largura`, `comprimento` | `DecimalField(5,2)` nullable | |
| `dimenssoes` | `BooleanField` default `True` | (nome com erro de grafia, mantido por compatibilidade) |
| `confrontacoes`, `medidas` | `TextField` | |

`save()` só chama `super().save()` — override vazio, **código morto residual** (provável resquício de um fix antigo, ver `CLAUDE.local.md` Task 0 do histórico de vendas que mexeu exatamente nisso).

`TypeLote` (`TextChoices`): `CONSTRUTORA`, `DISPONIVEL`, `EM_RESERVA`, `INDISPONIVEL`, `PRE-RESERVA`, `RESERVADO`, `PRE-VENDA`, `VENDIDO`, `ANALISE`.

Não há managers customizados no app.

---

## 3. Views (`views.py`) — todas Function-Based Views (nenhuma CBV, exceto `importarDados`)

| View | Tipo | Permissão | Descrição |
|---|---|---|---|
| `selectEmpreendimento` | FBV | `selectEmpreendimento` | Retorna JSON `{id, nome}` de um empreendimento (uso via AJAX) |
| `criarEmpreendimento` | FBV | `criarEmpreendimento` | GET/POST cadastro de empreendimento; tenta salvar imagens extras via `ImagemEmpreendimento` (**model inexistente**, ver §12) |
| `listaEmpreendimento` | FBV | `listaEmpreendimento` | Lista empreendimentos ativos vinculados ao usuário logado (via `UsuarioEmpreendimento`) |
| `alteraEmpreendimento` | FBV | `alterarEmpreendimento` | GET/POST edição; normaliza CNPJ pra 14 dígitos numéricos |
| `deleteEmpreendimento` | FBV, `@require_POST` | `deletarEmpreendimento` | Soft-delete (`is_ativo=False`) |
| `listaEmpreendimentoTabela` | FBV | `listaEmpreendimentoTabela` | Tabela com contagem de lotes por situação, por empreendimento |
| `listaQuadra` | FBV | `listaQuadra` | Lista quadras + lotes de um empreendimento, com filtro por situação e paginação (9/página) |
| `atualizarLotes` | FBV | `atualizarLotes` | Lista paginada (20/página) de lotes com filtro por quadra/número, pra edição em massa |
| `editarAtualizarLote` | FBV | `atualizarLotes` | GET/POST edição pontual de um lote (`AtualizarLoteForm`) |
| `importarDados` (CBV `View`) | CBV | nenhuma (**sem decorator de permissão**) | Importa quadras/lotes via planilha Excel (`pandas`) |
| `detalheEmpreendimento` | FBV | nenhuma (**sem decorator**) | Tela de detalhe: corretores vinculados, estatísticas de lotes, modelos de documento vinculados |
| `relatorioFinanceiro` | FBV | nenhuma (**sem decorator**) | Relatório com totais financeiros por situação de lote (HTML) |
| `alteraLote` | FBV | `reservarLote` | GET marca lote `DISPONIVEL→EM_RESERVA` e define prazo; POST grava dados do cliente e muda pra `PRE-RESERVA` |
| `reservadoDetalheEmpreendimento` | FBV | `reservadoDetalheEmpreendimento` | Detalhe de uma pré-reserva; checa se usuário é dono do lote ou admin, senão mostra `permissao.html` |
| `listaReservasTemporaria` | FBV | `listaReservasTemporaria` | Lista lotes `PRE-RESERVA` com busca e filtro por empreendimento |
| `liberaLote` | FBV | **decorator comentado** (`# @has_permission_decorator('liberaLote')`) | GET libera lote pra `DISPONIVEL` — **sem controle de acesso, aceita GET** (ver §12) |
| `cancelarReservadoTemporaria` | FBV | `cancelarReservadoTemporaria` | GET cancela pré-reserva, limpa cliente/telefone, redireciona pra `listar-quadras` |
| `cancelarReservadoTemporariaLista` | FBV | `cancelarReservadoTemporariaLista` | Igual à anterior, mas redireciona pra `lista-pre-reserva` |
| `renovaReserva` | FBV | `renovarReservaTemporaria` | GET renova prazo da pré-reserva |
| `gerarRelatorioLotes` | FBV | nenhuma (**sem decorator**) | Gera PDF (ReportLab) de lotes filtrados por situação/empreendimento — há uma versão antiga comentada (~80 linhas de código morto no final do arquivo) |
| `criarUsuarioEmpreendimento` | FBV, `@require_POST` | nenhuma (**sem decorator**) | Vincula/reativa corretores a um empreendimento (`UsuarioEmpreendimento`) — há bloco de código morto comentado embaixo (versão antiga da função) |
| `deleteUsuarioEmpreendimento` | FBV, `@require_POST` | `deleteUsuarioEmpreendimento` | Soft-delete do vínculo corretor↔empreendimento — **rota duplicada, ver §11/§12** |
| `modelo_vincular` | FBV, `@require_POST @login_required` | apenas login | Vincula `ModeloDocumento` ao empreendimento, controla "padrão por tipo" |
| `modelo_desvincular` | FBV, `@require_POST @login_required` | apenas login | Remove vínculo modelo↔empreendimento |
| `modelo_set_padrao` | FBV, `@require_POST @login_required` | apenas login | Marca vínculo como padrão do tipo (desmarca os demais) |
| `exportar_lotes` | FBV | `atualizarLotes` | Exporta lotes do empreendimento em `.xlsx` (openpyxl), marcando `[BLOQUEADO]` lotes com venda ativa (`ANALISE`/`PRE-VENDA`) |
| `importar_lotes` | FBV, `@require_http_methods(['POST'])` | `atualizarLotes` | Lê `.xlsx` exportado, calcula diff campo a campo, gera preview (não aplica ainda) |
| `importar_lotes_confirmar` | FBV, `@require_POST` | `atualizarLotes` | Aplica as alterações do preview (JSON serializado em campo hidden), ignora lotes com venda ativa |

---

## 4. URLs (`urls.py`)

| Path | Name | View |
|---|---|---|
| `` | `lista-empreendimento` | `listaEmpreendimento` |
| `insert_empreendimento/` | `criar-empreendimento` | `criarEmpreendimento` |
| `listar_empreendimento/` | `lista-empreendimento-tabela` | `listaEmpreendimentoTabela` |
| `select/<uuid:empreendimento_uuid>/` | `select-empreendimento` | `selectEmpreendimento` |
| `alterar_empreendimento/<uuid:uuid>/` | `alterar-empreendimento` | `alteraEmpreendimento` |
| `deleta_empreendimento/<uuid:empreendimento_uuid>/` | `deletar-empreendimento` | `deleteEmpreendimento` |
| `detalhe_empreendimento/<uuid:uuid>/` | `detalhe-empreendimento` | `detalheEmpreendimento` |
| `insert_arq/<uuid:uuid>/` | `arquivo` | `importarDados.as_view()` |
| `listar_quadras/<uuid:empreendimento_uuid>/` | `listar-quadras` | `listaQuadra` |
| `atualizar-lotes/<uuid:empreendimento_uuid>/` | `atualizar-lotes` | `atualizarLotes` |
| `atualizar-lotes/editar/<uuid:lote_uuid>/` | `editar-atualizar-lote` | `editarAtualizarLote` |
| `relatorio-lotes/` | `relatorio-lotes` | `gerarRelatorioLotes` |
| `insert_reserva_pre_reserva_lote/<uuid:preReserva_uuid>/` | `reservado-detalhes-pre-reserva-lote` | `reservadoDetalheEmpreendimento` |
| `listar_pre_reserva/` | `lista-pre-reserva` | `listaReservasTemporaria` |
| `cancela_reserva_lote/<uuid:lote_uuid>/` | `cancela-lote-pre-reserva` | `cancelarReservadoTemporaria` |
| `cancela_reserva_lote_lista/<uuid:lote_uuid>/` | `cancela-lote-pre-reserva-lista` | `cancelarReservadoTemporariaLista` |
| `renova_reserva_lote/<uuid:renova_uuid>/` | `renova-lote-pre-reserva` | `renovaReserva` |
| `libera_lote/<uuid:lote_uuid>/` | `libera-lote` | `liberaLote` |
| `alterar_lote/<uuid:uuid>/` | `alterar-lote` | `alteraLote` |
| `relatorio_financeiro/<uuid:uuid>/` | `relatorio-financeira` → `relatorio-financeiro` | `relatorioFinanceiro` |
| `usuariosempreendimento/` | `criar-usuario-empreendimento` | `criarUsuarioEmpreendimento` |
| `usuariosempreendimento/<uuid:usuario_empreendimento_uuid>/delete/` | `delete-usuario-empreendimento` | `deleteUsuarioEmpreendimento` |
| `empreendimento/<uuid:empreendimento_uuid>/modelo/vincular/` | `modelo-vincular` | `modelo_vincular` |
| `empreendimento/<uuid:empreendimento_uuid>/modelo/<uuid:vinculo_uuid>/desvincular/` | `modelo-desvincular` | `modelo_desvincular` |
| `empreendimento/<uuid:empreendimento_uuid>/modelo/<uuid:vinculo_uuid>/padrao/` | `modelo-set-padrao` | `modelo_set_padrao` |
| `detalhe_empreendimento/<uuid:empreendimento_uuid>/lotes/exportar/` | `exportar-lotes` | `exportar_lotes` |
| `detalhe_empreendimento/<uuid:empreendimento_uuid>/lotes/importar/` | `importar-lotes` | `importar_lotes` |
| `detalhe_empreendimento/<uuid:empreendimento_uuid>/lotes/importar/confirmar/` | `importar-lotes-confirmar` | `importar_lotes_confirmar` |

**Nota:** `delete-usuario-empreendimento` também existe registrada em `accounts/urls.py` com view quase-duplicada — já mapeado como débito conhecido em memória do projeto (`project_uuid` fase 5), não corrigido aqui.

---

## 5. Forms (`forms.py`)

- **`MultipleFileField`/`MultipleFileInput`** — helper genérico pra upload múltiplo (Django docs pattern). **Não usado em nenhum form atual** — código morto/preparado pra feature não implementada (o campo `Empreendimento` em `criarEmpreendimento` usa `request.FILES.getlist()` direto, sem usar este field).
- **`EmpreendimentoForm`** (ModelForm, criação) — `exclude=('is_ativo',)`. Validações: `clean_nome` (bloqueia nome duplicado ativo, orienta reativar se existir inativo com mesmo nome); `clean_cnpj` (normaliza, exige 14 dígitos, unicidade). Organiza campos em colunas via `widget.attrs['col']` (`left`/`right`/`endereco`/`representante`) — consumido pelo template.
- **`EmpreendimentoUpdateForm`** — praticamente duplicado do anterior (mesma normalização/validação de CNPJ, mesmos widgets), mas **sem `clean_nome`** (edição não valida duplicidade de nome) e inclui `codBanco` no config de placeholders.
- **`EmpreendimentoEnderecoForm`** — ModelForm só de endereço, **não referenciado por nenhuma view** (grep confirma zero uso em `views.py`) — código morto ou preparado para feature futura de wizard de endereço separado.
- **`ArquivoForm`** — form simples (`FileField`) usado por `importarDados`.
- **`LoteForm`** — ModelForm (`cliente_reserva`, `telefone`), com máscara e formatação de telefone pré-existente.
- **`AtualizarLoteForm`** — ModelForm (`valor_metro_quadrado`, `medidas`, `confrontacoes`, `dimenssoes`), usado em `editarAtualizarLote`.

---

## 6. Admin (`admin.py`)

- **`EmpreendimentoAdmin`** — `list_display` com dados bancários e uuid. `get_queryset`/`has_change_permission`/`has_view_permission` restringem superusuário vê tudo, demais usuários só empreendimentos vinculados via `UsuarioEmpreendimento`. Inline de `Quadra` está comentado (`#inlines = [QuadraInlineAdmin]`).
- **`QuadraAdmin`** — campos readonly via métodos (`get_nome_empr`, `get_tempo_reserva`, `get_logo_empr`), inline de `Lote` (`LoteInlineAdmin`, campos limitados).
- **`LoteAdmin`** — `list_display` com empreendimento derivado (`get_empreendimento`), busca por id/lote/situacao/uuid.
- **`UsuarioEmpreendimentoAdmin`** — registrado aqui embora o model pertença a `accounts` — acoplamento cruzado no admin (aceitável, é prática comum registrar admin de outro app quando há relação direta).

---

## 7. Templates (`templates/*.html`)

| Template | Usado por | Propósito |
|---|---|---|
| `empreendimento.html` | `criarEmpreendimento` | Formulário de cadastro de novo empreendimento |
| `update_empreendimento.html` | `alteraEmpreendimento` | Formulário de edição de empreendimento |
| `update_empreendimentoold.html` | **nenhuma view** | **Órfão** — versão antiga do form de edição, não referenciado em nenhum `.py` |
| `lista-empreendimentos.html` | `listaEmpreendimento` | Lista simples de empreendimentos do usuário |
| `lista-empreendimentos-tabela.html` | `listaEmpreendimentoTabela` | Tabela com contagem de lotes por situação |
| `detalhes-do-empreendimento.html` | `detalheEmpreendimento` | Tela central de detalhe: corretores, estatísticas, modelos de documento vinculados (maior template do app, 866 linhas) |
| `empreendimento_arq.html` | `importarDados` (GET) | Form simples de upload de arquivo pra importação de quadras/lotes |
| `lista-quadras.html` | `listaQuadra` | Grade de quadras/lotes com filtro de situação e paginação (878 linhas, maior do app) |
| `atualizar-lotes.html` | `atualizarLotes` | Lista de lotes pra edição em massa, com filtros |
| `editar-atualizar-lote.html` | `editarAtualizarLote` | Form de edição pontual de um lote |
| `importar-lotes-preview.html` | `importar_lotes` | Preview de diff antes de confirmar importação xlsx |
| `reserva-temporaria.html` | `alteraLote` | Form de reserva/pré-reserva de um lote específico |
| `detalhes-reserva-lote.html` | `reservadoDetalheEmpreendimento` | Detalhe de uma pré-reserva específica |
| `relatorio_de_reservas_temporario.html` | `listaReservasTemporaria` | Lista/busca de pré-reservas ativas |
| `relatorio-financeiro.html` | `relatorioFinanceiro` | Relatório financeiro HTML (totais por situação) |
| `permissao.html` | `reservadoDetalheEmpreendimento` | Tela de "sem permissão" quando usuário não é dono do lote nem admin |

---

## 8. Tasks / Celery / Cron (`tasks.py`, `cron.py`, `management/commands/registrar_tasks_beat.py`)

Fila dedicada `"empreendimentos"` para todas as tasks Celery.

| Task | Trigger | O que faz |
|---|---|---|
| `destravar_lotes_expirados` | manual/beat | Libera lotes `EM_RESERVA` com `tempo_reservado <= agora` → `DISPONIVEL`, limpa cliente/telefone. `select_for_update(skip_locked=True)` |
| `liberar_lotes_travados` | alias | Só chama `destravar_lotes_expirados()` — mantido por compatibilidade com Beat legado |
| `liberar_lotes_expirados` | manual/beat | Libera lotes `PRE-RESERVA` com `data_termina_reserva <= hoje` → `DISPONIVEL` |
| `voltar_lote_para_disponivel(lote_id)` | manual (admin) | Força um lote específico pra `DISPONIVEL` |
| `liberar_lotes_sem_venda` | **Beat, a cada 1 min** (registrada por `registrar_tasks_beat`) | Libera lotes `EM_RESERVA` sem `RegisterVenda` com `is_ativo=True` associado — é a task realmente agendada em produção |

`cron.py` — contém só `minha_tarefa()`, um logger de exemplo, **não é referenciado em lugar nenhum** (nem `django-crontab` nem chamada manual) — código morto/placeholder.

`registrar_tasks_beat.py` — management command que faz `get_or_create` de `PeriodicTask` `LIBERAR_LOTES_SEM_VENDA` → `empreendimentos.tasks.liberar_lotes_sem_venda`, intervalo 1 min. É o único ponto que liga a task 5 ao Celery Beat de fato (as outras 4 tasks não têm `PeriodicTask` registrada aqui — provavelmente idle ou disparadas manualmente).

---

## 9. Signals (`signal.py`)

Todo o conteúdo está **comentado** — havia um `post_save` em `Lote` que criaria `MensagemOutbox` ao mudar de situação, mas está desativado. `apps.py` também tem o `ready()` que importaria `signals`/`signals_notificacao` comentado — ou seja, **nenhum signal está ativo no app** atualmente.

---

## 10. Testes

`tests/conftest.py` — fixtures `admin_user`, `empreendimento`, `quadra`, `cliente_pf`.

`tests/test_empreendimentos.py` — cobre:
- `exportar_lotes` (sucesso, bloqueio por venda ativa, 403 anônimo)
- `importar_lotes` (atualização, ignora lote com venda ativa, erro de preço inválido, erro de status inválido)
- `importar_lotes_confirmar` (aplica alterações, ignora venda ativa, JSON inválido)
- Regressão específica: lote `ANALISE` sem `RegisterVenda` não deve gerar link de proposta-rascunho quebrado em `lista-quadras.html`

`tests/test_tasks.py` — cobre `liberar_lotes_sem_venda` extensivamente: sem venda, com venda ativa, com venda "CANCELADA mas is_ativo=True" (regressão de bug real), venda inativa, múltiplos lotes, queryset vazio.

**Não testado:** `criarEmpreendimento`, `alteraEmpreendimento`, `deleteEmpreendimento`, `listaEmpreendimento`, `listaQuadra`, `atualizarLotes`, `editarAtualizarLote`, `alteraLote`, `reservadoDetalheEmpreendimento`, `listaReservasTemporaria`, `liberaLote`, `cancelarReservadoTemporaria(Lista)`, `renovaReserva`, `gerarRelatorioLotes`, `criarUsuarioEmpreendimento`, `deleteUsuarioEmpreendimento`, `modelo_vincular/desvincular/set_padrao`, `importarDados` (upload de Excel), `relatorioFinanceiro`. Ou seja, a maior parte das views do app (~22 de 29) não tem cobertura automatizada — só o fluxo de exportar/importar/task de liberação está coberto.

---

## 11. Acoplamento com outros apps

**`empreendimentos` importa de:**
- `vendas.models.RegisterVenda` (views.py, tasks.py) — pra checar "venda ativa" antes de bloquear edição/exportação de lote
- `documentos.models.ModeloDocumento`, `EmpreendimentoDocumento` (views.py) — vínculo de modelos de documento por empreendimento
- `accounts.models.User`, `UsuarioEmpreendimento` (views.py, admin.py) — corretores vinculados

**Apps que importam de `empreendimentos`:**
- `vendas` (models.py, delete/create/detail/list_views.py) — `Lote`, `Empreendimento`, `LoteForm`
- `documentos` (services.py, views_documentos.py) — `Lote`, `Empreendimento`
- `accounts` (views.py, models.py) — `Empreendimento` (FK em `UsuarioEmpreendimento`)
- `dashboard` (views.py) — `Empreendimento`, `Lote`
- `mensagem` (signals.py) — `Lote`

Ou seja, há **acoplamento bidirecional real**: `empreendimentos` depende de `vendas` e `documentos`, que por sua vez dependem de `empreendimentos`. Não é um ciclo de import direto (Python resolve porque os imports de `vendas`/`documentos` em `empreendimentos/views.py` não são reimportados de volta no mesmo módulo), mas arquiteturalmente `empreendimentos` não é mais um app "de baixo nível" — está no meio do grafo de dependências, o que dificulta isolar/testar sozinho.

---

## 12. Observações técnicas (bugs, débitos, código morto)

1. **Bug real — `NameError` latente em `criarEmpreendimento`** (`views.py:99`): usa `ImagemEmpreendimento(...)` mas essa classe não existe em `models.py` nem é importada. Se o form de cadastro (`empreendimento.html`) tiver um campo de upload múltiplo chamado `Empreendimento` e o usuário enviar arquivos nele, a view quebra com `NameError` dentro do `try/except Exception` genérico — o erro é engolido e vira mensagem genérica "Erro ao criar empreendimento: name 'ImagemEmpreendimento' is not defined", mas o empreendimento em si já foi criado (commit acontece dentro do mesmo bloco `transaction.atomic()`, então na real a transação é revertida inteira — o empreendimento NÃO fica salvo, mas o usuário recebe erro confuso). Feature de "imagens do empreendimento" parece nunca ter sido implementada de fato.

2. **`liberaLote` sem controle de acesso** (`views.py:861`): decorator `@has_permission_decorator('liberaLote')` está comentado, aceita GET (efeito colateral em requisição idempotente por natureza HTTP), sem `@login_required` explícito na view (embora o middleware do projeto possa cobrir isso globalmente — não verificado aqui). Qualquer usuário autenticado consegue liberar qualquer lote de qualquer empreendimento sem checagem de vínculo.

3. **Views sem decorator de permissão**: `importarDados`, `detalheEmpreendimento`, `relatorioFinanceiro`, `gerarRelatorioLotes`, `criarUsuarioEmpreendimento` não têm `@has_permission_decorator`. Pode ser intencional (protegidas por middleware global de login) mas quebra o padrão do resto do arquivo, que usa o decorator sistematicamente — vale confirmar se é lacuna real.

4. **Rota duplicada `delete-usuario-empreendimento`**: registrada tanto aqui quanto em `accounts/urls.py`, com views quase-idênticas — já mapeado como débito conhecido em sessões anteriores (memória `project_uuid`, fase 5), não é achado novo.

5. **Tipos de dado financeiro como `CharField`**: `Lote.area` e `Lote.valor_metro_quadrado` são `CharField`, não `DecimalField`. Toda conta (`relatorioFinanceiro`, `listaQuadra`, `gerarRelatorioLotes`, `exportar_lotes`) faz parsing manual (`float()`/`Decimal(str(...).replace(',', '.'))`) com `try/except` silencioso que retorna `0` em caso de erro — mascarável para dados malformados dando totais errados sem alerta.

6. **`Lote.save()` é override vazio** (`models.py:166`) — só chama `super().save()`, não faz nada. Resquício de lógica removida (o histórico do projeto em `CLAUDE.local.md` menciona explicitamente "Task 0: Fix `Lote.save()` — remover sobrescrita `tempo_reservado`" numa sessão anterior de vendas) — o override em si virou morto, poderia ser removido.

7. **Código morto comentado**: bloco de ~80 linhas de versão antiga de `gerarRelatorioLotes` (final de `views.py`), versão antiga comentada de `criarUsuarioEmpreendimento`, `signal.py` inteiro comentado, `cron.py` com função de exemplo nunca usada, `apps.py` com `ready()` comentado.

8. **Templates/forms órfãos**: `update_empreendimentoold.html` (não referenciado por nenhuma view), `EmpreendimentoEnderecoForm` (não referenciado por nenhuma view), `MultipleFileField`/`MultipleFileInput` (definidos mas não usados por nenhum form do app).

9. **Mensagem de erro incorreta em `_validate_logo_arquivo`**: diz "Envie JPG ou PNG" mas o validador só aceita `jpg`/`jpeg` (`ext not in ('jpg', 'jpeg')`) — PNG é rejeitado apesar da mensagem dizer que é aceito.

10. **`EmpreendimentoForm.clean_nome` bloqueia reativação direta**: se existe empreendimento inativo com mesmo nome, força o usuário a "reativar" em vez de criar novo — mas não há nenhuma view/rota de "reativar empreendimento" no app. Ou seja, a mensagem de erro aponta para um fluxo que não existe na UI.

11. **`EmpreendimentoUpdateForm` não repete a validação de nome duplicado** presente em `EmpreendimentoForm` — inconsistência: dá pra editar um empreendimento e colocar nome duplicado de outro ativo sem barreira (só CNPJ é revalidado em ambos).

12. **`representante_fields`, `representante_nome/cpf/rg`, `matricula`, `cidade_foro`** foram adicionados via migration `0058` — parecem servir de base pros dados usados em geração de documentos/contratos (`documentos` app), mas não há `FK`/vínculo formal a `ClienteRepresentante` (de `clientes` app, adicionado em sessão recente) — são campos soltos no `Empreendimento`, papéis de representante do empreendimento (não do cliente).

13. **`quadra` related_name confuso**: `Quadra.empr` tem `related_name='empreendimento'` — semanticamente deveria indicar "quadras do empreendimento", não "o empreendimento da quadra". Não usado hoje, mas armadilha pra manutenção futura.
