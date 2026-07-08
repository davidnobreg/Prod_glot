# Módulo: clientes

> Mapeamento do estado atual do código. Documenta o que existe — não é proposta de mudança.
> Gerado em 2026-07-07.

---

## 1. Visão Geral

App responsável pelo cadastro e gestão de clientes (pessoa física ou jurídica): dados pessoais,
endereço, cônjuge (desnormalizado no próprio model), telefones e documentos de identificação
(RG, CPF, CNH, comprovante de residência, etc.). Inclui um wizard multi-etapa (rascunho →
finalização) que salva o cliente incompleto (`is_ativo=False`) a cada passo e só ativa no final,
disparando uma task Celery de pós-processamento dos documentos enviados.

Consumido por `vendas` (FK `RegisterVenda.cliente`), que também é a razão de `deleteCliente`
bloquear exclusão se houver venda ativa.

---

## 2. Estrutura de Arquivos

```
clientes/
  models.py                225 linhas — Cliente, ClienteDocumento, ClienteTelefone
  forms.py                 427 linhas — ClienteBaseForm, ClienteForm, ClienteUpdateForm,
                                        ClienteEnderecoForm, ClienteConjugeForm,
                                        ClienteTelefoneForm, ClienteDocumentoForm
  views.py                 670 linhas — todas as views do app (sem subpacote)
  urls.py                   20 linhas — URLconf ativa (uuid em todos os params)
  admin.py                  26 linhas — ClienteAdmin + 2 inlines
  serializers.py            62 linhas — ClienteSerializer (DRF, não conectado — ver §10)
  tasks.py                  29 linhas — processar_documentos_pendentes (Celery)
  apps.py                    6 linhas
  templatetags/
    format_filters.py       37 linhas — initials, format_documento
  tests/                  1071 linhas total (ver §9)
  templates/                6 arquivos .html (ver §8)
  migrations/                34 arquivos (ver §11)
```

---

## 3. Models (`clientes/models.py`)

### `Cliente`

| Campo | Tipo | Observação |
|---|---|---|
| `id` | BigAutoField | PK legada, ainda existe ao lado do uuid |
| `uuid` | UUIDField | chave pública, usada em todas as rotas |
| `name` | CharField(100) | normalizado pra upper no `save()` |
| `nome_usual` | CharField(50) | opcional |
| `documento` | CharField(18), **unique** | CPF ou CNPJ, só dígitos (normalizado no `save()`) |
| `numero_rg`, `orgao_emissor_rg` | CharField | — |
| `email` | EmailField(200), **unique** | normalizado pra lower no `save()` |
| `estado_civil` | CharField(22, choices=`choices_estado_civil`) | tupla simples, não `TextChoices` (§10) |
| `renda` | CharField(20) | **não é DecimalField** — histórico de 4 migrations alternando o tipo (§11, §10) |
| `is_ativo` | BooleanField(default=`True`) | flag de soft-delete |
| `end_rua`, `end_complemento`, `end_numero`, `end_bairro`, `end_cep`, `end_cidade`, `end_estado` | CharField | endereço desnormalizado (era model `ClienteEndereco` separado, incorporado na migration 0025-0027) |
| `conj_nome`, `conj_numero_rg`, `conj_orgao_emissor_rg`, `conj_documento` | CharField | cônjuge desnormalizado (mesma origem) |

`choices_estado` (module-level, linha 11-18): tupla de 26 estados + DF (sem "todos os estados",
o BR tem 26+DF = 27, confere).

`Cliente.validar_cpf` (staticmethod, linhas 81-92): **código morto**, nunca chamado — a validação
real usada pelo form é a função module-level `forms.validar_cpf` (implementação diferente).

`Cliente.save()` (linhas 98-108): normaliza `name` (upper+strip), `email` (lower+strip),
`documento` (remove tudo que não é dígito via regex).

### `ClienteDocumento`

Tabela auxiliar de documentos/anexos.

| Campo | Tipo | Observação |
|---|---|---|
| `uuid` | UUIDField, unique | chave pública |
| `cliente` | FK → `Cliente` | `CASCADE`, `related_name='arquivos_cliente'` |
| `tipo` | CharField(50, choices) | `TIPO_CHOICES_PF` (RG, RG_NOVO, CPF, CNH, COMPROVANTE_ESTADO_CIVIL, COMPROVANTE_RESIDENCIA, OUTROS) ou `TIPO_CHOICES_PJ` (CNPJ, CONTRATO_SOCIAL, RG_CPF_ADMINISTRADOR, COMPROVANTE_RESIDENCIA, OUTROS) |
| `pertence_a` | CharField(10, choices) | `TITULAR`/`CONJUGE`, default `TITULAR` |
| `status` | CharField(20, choices) | `processando`/`disponivel`/`erro`, default `disponivel` |
| `arquivo` | FileField | `upload_to='clientes/documentos/'` — **sem validador de extensão/tamanho no model nem no form** (§10) |
| `descricao` | CharField(200) | opcional |
| `criado_em` | DateTimeField(auto_now_add) | — |

`Meta.ordering = ['-criado_em']`. Hard delete puro (sem soft-delete/status de exclusão) — ver §4.

### `ClienteTelefone`

| Campo | Tipo | Observação |
|---|---|---|
| `id` | BigAutoField | PK |
| `cliente` | FK → `Cliente` | `CASCADE`, `related_name='telefones'` |
| `numero` | CharField(15) | `RegexValidator` formato `(99) 99999-9999` |
| `tipo` | CharField(10, choices) | celular/fixo/recado/whatsapp/outro, default `celular` |
| `observacao` | CharField(100) | opcional |
| `is_ativo` | BooleanField(default=`True`) | **nunca setado como `False` em nenhum fluxo real** — telefones são hard-deletados em `atualizarCliente`/`_wizard_save_contatos` (§10) |

---

## 4. Estados e Fluxos

### `Cliente.is_ativo` — soft-delete + rascunho de wizard (duplo uso do mesmo flag)

```
is_ativo=False (recém-criado via wizard, rascunho)
  → (wizard_finalizar, validação ok)  is_ativo=True   [cliente "existe" de fato]

is_ativo=True (cliente ativo normal)
  → (deleteCliente, sem venda ativa)  is_ativo=False  [soft-delete, email ofuscado — ver §10 bug #2]
  → (deleteCliente, com venda ativa exceto CANCELADA)  bloqueado, mensagem de erro, sem mudança
```

`is_ativo=False` tem **dois significados sobrepostos** no mesmo campo: "rascunho de wizard não
finalizado" e "cliente desativado/excluído". Um cliente soft-deletado teoricamente poderia ser
reaberto pelo fluxo de wizard (`_wizard_get_draft` filtra só por `uuid` + `is_ativo=False`, sem
distinguir rascunho de exclusão) — não confirmado como bug ativo, mas é uma sobreposição de
semântica que merece atenção antes de qualquer mudança em ambos os fluxos.

### `ClienteDocumento.status` (fluxo do wizard)

```
processando (setado em wizard_arquivo_add)
  → (processar_documentos_pendentes, Celery, dispara em wizard_finalizar) disponivel
  → (mesma task, se doc.arquivo.size lançar exceção) erro
```

Fora do wizard (`adicionar_documento_cliente`, uso normal pós-cadastro), o documento já nasce
`disponivel` (default do model) — a task só roda para os que passaram pelo wizard.

---

## 5. Views (`clientes/views.py`)

Todas FBV, protegidas por `@has_permission_decorator(...)` (django-role-permissions). Nenhuma
usa `@login_required` isoladamente.

| Rota | View | Permissão | Método | O que faz |
|---|---|---|---|---|
| `insert_cliente/` | `criarCliente` | `criarCliente` | GET/POST | form completo (dados+endereço+cônjuge+telefones) numa página só, transaction.atomic |
| `select/<uuid:cliente_uuid>/` | `selectCliente` | `selectCliente` | GET | retorna JSON simples (uuid/name/documento/email) — usado por autocomplete/AJAX |
| `update/<uuid:cliente_uuid>/` | `atualizarCliente` | `alterarCliente` | GET/POST | edição completa, mesmo padrão de `criarCliente`, diff de telefones (cria só os novos, deleta os removidos) |
| `delete_cliente/<uuid:cliente_uuid>/` | `deleteCliente` | `deletarCliente` | **sem checagem de método** | soft-delete, bloqueia se venda ativa (ver bug §10 #1) |
| `listar_clientes/` | `listaCliente` | `relatorioCliente` | GET | lista paginada (12/página), busca por nome/documento/email, só `is_ativo=True` |
| `listar_clientes_relatorio/` | `listaClienteRelatorio` | `relatorioClienteRelatorio` | GET | segunda listagem, praticamente idêntica (10/página) — ver §10 |
| `<uuid:cliente_uuid>/documentos/adicionar/` | `adicionar_documento_cliente` | `alterarCliente` | POST (fallback redirect em GET) | anexa documento a cliente já existente |
| `documentos/<uuid:documento_uuid>/excluir/` | `excluir_documento_cliente` | `alterarCliente` | POST-only (`Http404` senão) | hard-delete do documento |
| `<uuid:cliente_uuid>/wizard/arquivo-add/` | `wizard_arquivo_add` | `criarCliente` | POST (405 senão) | anexa documento a **rascunho** (`is_ativo=False`), status inicial `processando` |
| `<uuid:cliente_uuid>/wizard/arquivo-del/<uuid:documento_uuid>/` | `wizard_arquivo_del` | `criarCliente` | POST (405 senão) | remove documento de rascunho |
| `wizard/salvar-passo/` | `wizard_salvar_passo` | `criarCliente` | POST (405 senão) | despacha por `step_id` (`step-1`/`step-2`/`step-4`/`step-5`) pra um dos 4 `_wizard_save_*` |
| `<uuid:cliente_uuid>/wizard/finalizar/` | `wizard_finalizar` | `criarCliente` | POST (405 senão) | valida obrigatórios, ativa (`is_ativo=True`), dispara Celery via `transaction.on_commit` |

Helpers privados (não são views, mas centrais ao fluxo): `_wizard_get_draft`,
`_wizard_save_step1/conjuge/endereco/contatos`, `_wizard_validar_finalizacao`,
`_normalize_telefones`/`_normalize_telefones_rich`, `_render_cliente_form`, `_get_tipo_pessoa`,
`_endereco_preenchido`.

---

## 6. Regras de Negócio Implementadas

- **Endereço obrigatório para cadastro/edição completa** (`views.py:165`, `273`): mesmo os campos
  do model sendo `blank=True`, a view exige os 6 campos de endereço preenchidos
  (`_endereco_preenchido`) antes de aceitar o POST de `criarCliente`/`atualizarCliente`.
- **Ao menos 1 telefone obrigatório** (`views.py:174-181`, `282-290`): mesmo padrão — regra de
  view, não de model/form.
- **Cônjuge obrigatório se casado** (`views.py:183-192`, `292-302`): só quando
  `estado_civil == 'casado'`; ao mudar de casado→outro em `atualizarCliente`, os campos `conj_*`
  são explicitamente zerados (`views.py:311-315`).
- **Diff de telefones na edição** (`views.py:318-326`): calcula `numeros_recebidos - numeros_existentes`
  para criar só os novos, e deleta (hard-delete) os que saíram da lista — não usa `is_ativo`.
- **Bloqueio de exclusão com venda ativa** (`views.py:660`): `deleteCliente` consulta
  `vendas.RegisterVenda` (import local pra evitar ciclo) e bloqueia se existir venda
  `exclude(tipo_venda='CANCELADA')`.
- **Soft-delete ofusca e-mail** (`views.py:664-665`): ao desativar, se havia email, vira
  `deleted_{uuid}@example.com` — libera o e-mail original pra reuso (mas não o `documento`, §10).
- **Wizard — tipo de pessoa dinâmico**: `_get_tipo_pessoa` (linha 94-97) deriva PF/PJ pelo
  tamanho do `documento` (11 = PF, 14 = PJ) e isso reflete em labels do form
  (`ClienteBaseForm._apply_tipo_pessoa_labels`, `forms.py:131-145`) e nos choices de
  `ClienteDocumentoForm` (`views.py:413-420`).
- **Validação de finalização do wizard** (`_wizard_validar_finalizacao`, `views.py:72-86`):
  exige `name`/`documento`/`email`, os 6 campos de endereço, ao menos 1 telefone
  (`cliente.telefones.exists()`), e `conj_nome` se casado — regra de negócio pura, sem teste
  unitário dedicado (§9).
- **Task Celery pós-finalização** (`views.py:589-591`, `tasks.py`): `transaction.on_commit`
  garante que o `.delay()` só dispara após o commit do `is_ativo=True`; a task varre documentos
  `processando` do cliente e marca `disponivel` (ou `erro` se `doc.arquivo.size` falhar).
- **Validação de CPF/CNPJ** (`forms.py:44-69`, `217-230`, `319-329`): dígito verificador
  completo para os dois formatos, aplicado em 3 pontos (form principal, form de cônjuge —
  implementações separadas, não uma função compartilhada única, §10).
- **Unicidade de `email`/`documento` sem excluir inativos** (`forms.py:210-213`, `225-229`):
  `clean_email`/`clean_documento` fazem `Cliente.objects.filter(...)` **sem** `is_ativo=True` —
  reforça o bug §10 #2 (documento de cliente soft-deletado nunca pode ser reaproveitado).

---

## 7. Services e Signals

Não existe `clientes/services.py` nem `clientes/signal.py` — toda a lógica de negócio está
dentro de `views.py` (funções privadas `_wizard_*`/`_normalize_*`/`_render_cliente_form`), sem
separação em camada de serviço. Diferente de `vendas`, que tem `services.py` dedicado.

---

## 8. Templates

| Template | Uso | Stack |
|---|---|---|
| `cliente.html` | `criarCliente` (GET/POST inválido) | Bootstrap/AdminLTE |
| `cliente_update.html` | `atualizarCliente` (GET/POST inválido) | Bootstrap/AdminLTE |
| `lista_cliente.html` | `listaCliente` | Bootstrap/AdminLTE |
| `lista_cliente_relatorio.html` | `listaClienteRelatorio` | Bootstrap/AdminLTE |
| `delete_cliente.html` | **nunca renderizado** — `deleteCliente` só faz `redirect`, nenhuma view chama `render()` com este template (§10) | Bootstrap/AdminLTE |
| `relatorio.html` | não referenciado por nenhuma view atual do app (verificar uso cross-app antes de considerar órfão) | Bootstrap/AdminLTE |

Nenhum template deste app está em Tailwind ainda (diferente de `vendas/lista_analise.html`).

---

## 9. Cobertura de Testes

1071 linhas de teste (pytest, fixtures em `conftest.py`).

| Arquivo | Cobre |
|---|---|
| `test_models.py` | `Cliente.__str__`, normalização em `save()` (upper/lower/strip documento), unicidade de documento/email (`IntegrityError`) |
| `test_views.py` | `criarCliente`/`atualizarCliente` (GET, POST válido, POST casado sem cônjuge, CPF duplicado, bloqueio anônimo 403), `validar_cpf` (função de `forms.py`), `ClienteForm`/`ClienteConjugeForm` |
| `test_cliente_documento.py` | `ClienteDocumento` (criação PF/PJ, `__str__`, `related_name`, cascade delete), `ClienteDocumentoForm` (choices por tipo_pessoa), `adicionar_documento_cliente`/`excluir_documento_cliente` (GET redireciona, POST válido/inválido, anônimo bloqueado, GET em excluir → 404) |
| `test_integration.py` | Contexto de `atualizarCliente`, listagem (`lista-cliente`: ativo aparece/inativo não aparece), soft-delete (`delete-cliente`: marca inativo, cliente com telefone não quebra, **cliente com venda ativa bloqueado**), fluxo casado→solteiro apaga dados de cônjuge, redirect pós-criação |
| `test_wizard.py` | Fluxo completo via Playwright E2E: navegação entre steps, upload de documento, rascunho salvo no banco, labels dinâmicos PF/PJ |

**Sem teste dedicado:**
- `selectCliente` (view AJAX) — nenhum teste.
- `listaClienteRelatorio` — nenhum teste (só `listaCliente` é testada).
- `wizard_arquivo_add`/`wizard_arquivo_del` (endpoints JSON diretos) — só cobertos indiretamente
  via Playwright, sem teste unitário isolado (ex.: `cliente_uuid` de cliente já ativo → 404, não
  testado).
- `wizard_salvar_passo`/`_wizard_save_step1/conjuge/endereco/contatos` — sem teste unitário direto
  (só E2E). Casos não cobertos: `step_id` desconhecido, `cliente_uuid` inválido/vazio.
- `wizard_finalizar`/`_wizard_validar_finalizacao` — sem teste garantindo bloqueio por campo
  obrigatório faltando, nem que o Celery task é de fato agendado.
- `deleteCliente` via GET — não testado (é o bug crítico §10 #1; um teste `client.get(url)`
  provavelmente passaria e exporia o problema).
- `ClienteTelefoneForm` — sem teste dedicado.
- `ClienteSerializer` (DRF) — sem teste (e nem está conectado a rota alguma, §10).
- `clientes/tasks.py::processar_documentos_pendentes` — sem teste unitário (sucesso,
  `Cliente.DoesNotExist`, exceção/retry).
- Templatetags `initials`/`format_documento` — sem teste unitário direto.
- `admin.py` — sem teste (baixa prioridade, aceitável).

---

## 10. Débitos Técnicos e Achados

1. **`deleteCliente` não checa `request.method`** — `views.py:655-671`: desativa o cliente
   independentemente do método HTTP. Diferente de `excluir_documento_cliente` (`raise Http404`
   se não POST) e das views `wizard_*` (retornam 405). O template usa `<form method="post">`
   (`lista_cliente.html:231`), então a UI normal não expõe isso — mas a view em si aceita GET,
   que não passa pelo middleware de CSRF (só métodos "unsafe" passam). Mesmo anti-pattern já
   corrigido em `vendas` (`CancelarReservadoCadastroView`).

2. **Soft-delete não libera `documento`** — `views.py:663-666`: só `email` é ofuscado
   (`deleted_{uuid}@example.com`); `documento` permanece intacto. Como `documento` é
   `unique=True` e `clean_documento` (`forms.py:225-229`) não exclui inativos da checagem de
   duplicidade, o CPF/CNPJ de um cliente desativado nunca pode ser recadastrado — inconsistente
   com a intenção clara (pelo tratamento do email) de permitir reaproveitar o "slot".

3. **Upload de documento sem validação server-side** — `forms.py:426`
   (`ClienteDocumentoForm.arquivo`): só `widget.attrs['accept']` (client-side, contornável via
   POST direto). Model `ClienteDocumento.arquivo` (`models.py:183`) também não tem
   `FileExtensionValidator` nem limite de tamanho — diferente de `vendas.VendaDocumento`, que já
   tem `validate_documento_assinado` (pdf/jpg/jpeg/png, máx 10MB, migration 0066).

4. **Três implementações paralelas de validação de CPF/CNPJ** —
   `models.Cliente.validar_cpf` (morto, `models.py:81-92`), `forms.validar_cpf`/`validar_cnpj`
   (`forms.py:44-69`, algoritmo diferente do de `models.py`), reaplicadas separadamente em
   `clean_documento` (`forms.py:217-230`) e `clean_conj_documento` (`forms.py:319-329`) — sem
   função compartilhada única.

5. **`renda` como `CharField`** — `models.py:50`. Histórico de instabilidade: migrations
   0017/0018/0020/0021 alternaram entre `CharField`↔`DecimalField`↔`CharField` em menos de um
   mês. Parsing feito manualmente em `_parse_money` (`forms.py:192-203`) via replace de string —
   frágil mas funcional; sem agregação ORM possível no estado atual.

6. **`listaCliente` e `listaClienteRelatorio` quase idênticas** — `views.py:339-397`: mesmo
   queryset base (`is_ativo=True`, mesmo prefetch de telefones, mesma busca por
   nome/documento/email), só diferem em paginação (12 vs 10) e template — candidatas a
   unificação.

7. **Indentação inconsistente** — `forms.py` inteiro em tabs; `views.py` misto (linhas 1-401 em
   espaços, linhas 406+ em tabs, a partir de `wizard_arquivo_add`) — sinal de autoria/época
   diferente (o bloco em tabs corresponde exatamente às views do wizard, adicionadas depois).
   Risco de `TabError` se algum editor normalizar parcialmente.

8. **`choices_estado`/`choices_estado_civil` como tuplas simples** — `models.py:11-18`, `24-31` —
   em vez de `models.TextChoices`, inconsistente com o padrão mais moderno usado em outros apps
   (ex. `vendas.TypeVenda`).

9. **`ClienteTelefone.is_ativo` nunca setado como `False`** — `models.py:217`: campo existe,
   default `True`, é filtrado em `listaCliente`/`listaClienteRelatorio`
   (`views.py:345`, `377`), mas telefones são sempre hard-deletados
   (`views.py:326`, `_wizard_save_contatos` `views.py:554`) — nunca desativados. Campo
   efetivamente morto na prática.

10. **`ClienteSerializer` (DRF) não conectado** — `serializers.py` inteiro: nenhuma
    view/viewset/URL router do projeto referencia essa classe (confirmado via busca em todo o
    repo) — esqueleto de API que nunca foi ligado a uma rota.

11. **Template `delete_cliente.html` órfão** — nunca é passado a um `render()`; `deleteCliente`
    só faz `redirect`. Página de confirmação completa (com mensagens de status `0`-`3`) que não é
    mais alcançável por nenhuma rota.

12. **Rota comentada morta** — `urls.py:19`: `# path('listar_clientes_filtro/', views.reports, ...)`
    — a view `reports` nem existe mais em `views.py`.

13. **Lógica de negócio pesada dentro das views** — `criarCliente`/`atualizarCliente`
    (`views.py:143-331`) concentram validação de endereço, cônjuge, telefones e
    `transaction.atomic()` inline, com duplicação significativa de blocos entre as duas funções.
    Diferente de `vendas`, que tem `services.py` — aqui não existe camada de serviço.

14. **Sobreposição de semântica em `is_ativo`** (ver §4) — mesmo campo usado tanto para
    "rascunho de wizard não finalizado" quanto para "cliente soft-deletado". Não confirmado como
    bug ativo, mas merece atenção antes de qualquer alteração nos dois fluxos.

15. **`wizard_salvar_passo` sem checagem de ownership do rascunho** — `views.py:462-480`:
    qualquer usuário com permissão `criarCliente` pode editar rascunho de outro usuário se
    souber o `cliente_uuid` (mitigado por só afetar rascunhos `is_ativo=False`, impacto baixo).

---

## 11. Migrations — Histórico Estrutural Relevante

34 migrations no total. Marcos relevantes:

| Migration | Mudança |
|---|---|
| `0017`–`0018`, `0020`–`0021` | ajustes sucessivos em `renda` (`CharField`↔`DecimalField`↔`CharField`, em ~1 mês) |
| `0019` | ajuste em `documento` |
| `0022`–`0023` | adiciona `uuid` em `Cliente` (pré-migração IDOR) |
| `0024` | adiciona `nome_usual` |
| `0025`–`0027` | **incorpora endereço e cônjuge no `Cliente`** — modelos `ClienteEndereco`/`ClienteConjuge` (não vistos neste mapeamento, já removidos) tiveram os dados copiados via `RunPython` (0026) e as tabelas antigas removidas (0027) |
| `0028` | adiciona campos de arquivo direto no `Cliente` (`comprovante_residencia`, `foto_cpf`, etc. — nomes sugerem uma abordagem anterior de anexos antes de existir `ClienteDocumento`) |
| `0029` | adiciona doc de cônjuge (RG/certidão) — provavelmente parte da mesma abordagem anterior |
| `0030` | **cria `ClienteDocumento`** (tabela auxiliar atual) |
| `0031` | **remove os campos de arquivo direto do `Cliente`** (revertendo 0028/0029 — migração para o padrão de tabela auxiliar) |
| `0032` | adiciona `status` em `ClienteDocumento` |
| `0033` | adiciona `pertence_a` e choice `RG_NOVO` |
| `0034` | adiciona `uuid` em `ClienteDocumento` |

Sequência 0028→0029→0030→0031 mostra uma mudança de abordagem em andamento: campos de arquivo
direto no `Cliente` foram tentados primeiro, depois abandonados em favor da tabela auxiliar
`ClienteDocumento` — consistente com o que existe hoje no model.

---

## 12. Pendências / Próximos Passos

Detalhado com estimativas no relatório de auditoria: `C:\Users\David\dev-vault\GLOT\revisoes\clientes-2026-07-07.md`.

- Corrigir `deleteCliente` para exigir POST (achado #1).
- Ofuscar/liberar `documento` no soft-delete, igual já é feito com `email` (achado #2).
- Adicionar validação server-side de tipo/tamanho em `ClienteDocumentoForm`/`ClienteDocumento`
  (achado #3).
- Unificar as 3 implementações de validação de CPF/CNPJ (achado #4).
- Escrever testes para `selectCliente`, `listaClienteRelatorio`, views de wizard,
  `_wizard_validar_finalizacao`, `deleteCliente` via GET, `ClienteTelefoneForm`, `tasks.py` (§9).
- Remover código morto: `Cliente.validar_cpf`, `ClienteSerializer`, `delete_cliente.html`, rota
  comentada em `urls.py` (achados #10, #11, #12).
- Avaliar consolidação de `listaCliente`/`listaClienteRelatorio` e extração de service layer para
  `criarCliente`/`atualizarCliente` (achados #6, #13) — decisão de arquitetura, não mexer sem
  autorização.
- Situação de backup do projeto (banco + `media_compartilhada`, onde ficam os documentos deste
  app) é risco crítico cross-cutting — ver seção dedicada no relatório de auditoria.
