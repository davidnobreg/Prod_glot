# Módulo: vendas

> Mapeamento do estado atual do código. Documenta o que existe — não é proposta de mudança.
> Gerado em 2026-07-07.

---

## 1. Visão Geral

App responsável pelo ciclo de vida comercial do lote: reserva, análise (desconto), pré-venda,
efetivação da venda e cancelamento. Também controla o fluxo de documentos assinados
(proposta/contrato) vinculados a cada venda, com aprovação/rejeição e histórico por ciclo.

Depende de `empreendimentos` (Lote, Empreendimento), `clientes` (Cliente, ClienteDocumento,
ClienteTelefone), `documentos` (ModeloDocumento, DocumentoGerado) e `accounts` (User).

---

## 2. Estrutura de Arquivos

```
vendas/
  models.py                 162 linhas — RegisterVenda, RegisterVendaIntercalada, VendaDocumento
  forms.py                  424 linhas — RegisterVendaForm
  services.py                78 linhas — checklist_documentos_cliente, documento_gerado_mais_recente
  signal.py                   0 linhas — vazio, sem signals registrados
  urls.py                    63 linhas — URLconf ativa (uuid)
  urls_old.py                21 linhas — morta, quebrada (ver §10)
  admin.py                   32 linhas — RegisterVendaAdmin
  views/
    create_views.py         724 linhas — EfetivarVendaView, CriarVendaView, CriarReservadoView,
                                          ReservaTemporariaView, RenovaReservaView, AceitaReservaView
    delete_views.py         110 linhas — CancelarVendaView, CancelarReservadoCadastroView,
                                          CancelarReservaView, CancelarAceiteReservaView
    detail_views.py         464 linhas — ReservadoView, AnaliseView, ReservadoDetalheView,
                                          PreVendaDetalheView, VendaDocumentoUploadView,
                                          VendaDocumentoAprovarView, VendaDocumentoRejeitarView
    list_views.py            288 linhas — ListarendaRelatorioView, RelatorioReservaView,
                                          ListaVendaView, ListasAnalisesView
  management/commands/
    arquivar_documentos_duplicados.py   67 linhas
    vincular_documentos_pendentes.py    86 linhas
  tests/                    4207 linhas total (ver §9)
  templates/                16 arquivos .html (ver §8)
  migrations/                67 arquivos (ver §11)
```

---

## 3. Models (`vendas/models.py`)

### `TypeVenda` (TextChoices)
`CANCELADA`, `RESERVADO`, `VENDIDO`, `ANALISE`, `NAO_ACEITE` (valor `'NAO-ACEITE'`, com hífen),
`PRE_VENDA` (valor `'PRE-VENDA'`).

### `RegisterVenda`
Model central — uma linha por reserva/venda de um lote.

| Campo | Tipo | Observação |
|---|---|---|
| `uuid` | UUIDField | chave pública, migrada nas fases anteriores |
| `lote` | OneToOne → `empreendimentos.Lote` | `SET_NULL`, `related_name='reg_venda'` |
| `cliente` | FK → `clientes.Cliente` | `SET_NULL` |
| `corretor` | FK → `accounts.User` | `SET_NULL`, `related_name='corretor'` |
| `user` | FK → `accounts.User` | `SET_NULL`, `related_name='vendas'` — quem criou o registro |
| `aceite_proposta` | FK → `accounts.User` | `SET_NULL` — quem aceitou a reserva em análise |
| `tipo_venda` | CharField(choices=TypeVenda) | estado do fluxo |
| `is_ativo` | BooleanField | default `False` |
| `dt_reserva`, `dt_venda`, `create_at`, `dt_primeira_parcela` | DateField | — |
| `valor_inicio_contrato` | DecimalField(12,2) | **não é preenchido pelo form** (ver §6/§10) |
| `valor_financiado` | DecimalField(50,2) | valor total pra fins de exibição/parcelamento |
| `valor_sinal`, `valor_entrada`, `valor_parcela`, `valor_desconto` | DecimalField(12,2) | — |
| `reajuste` | BooleanField | default `True` |
| `quantidade_parcelas`, `quantidade_parcelas_pagas` | IntegerField | — |
| `observacao` | TextField | — |
| `corretor_nome` | CharField | snapshot de texto, independente da FK `corretor` |

### `RegisterVendaIntercalada`
FK → `RegisterVenda` (`related_name='intercaladas'`), `quantidade_parcelas_intercalada`,
`valor_intercalada` (**CharField**, não Decimal — inconsistente com o resto do model).

### `VendaDocumento`
Upload de documento assinado (proposta/contrato) vinculado a uma venda.

| Campo | Tipo | Observação |
|---|---|---|
| `uuid` | UUIDField | chave pública (Fase 2 da migração uuid) |
| `venda` | FK → `RegisterVenda` | `CASCADE`, `related_name='documentos_assinados'` |
| `tipo` | CharField(choices) | `proposta_assinada`, `contrato_assinado`, `outros` |
| `arquivo_assinado` | FileField | validado por `validate_documento_assinado` (pdf/jpg/jpeg/png, máx 10MB) |
| `status` | CharField(choices) | `pendente`/`enviado`/`aprovado`/`rejeitado`/`arquivado` |
| `ciclo` | PositiveIntegerField | agrupa idas e vindas de documento (histórico) |
| `enviado_por`, `aprovado_por` | FK → `User` | `SET_NULL` |
| `documento_gerado` | FK → `documentos.DocumentoGerado` | `SET_NULL`, lastro com o documento gerado pelo sistema |

Manager custom `VendaDocumentoQuerySet.vigentes()` — exclui `status='arquivado'`.

Constraint: `UniqueConstraint(fields=['venda','tipo'], condition=Q(status='aprovado'), name='unico_aprovado_por_venda_tipo')`
— só pode haver 1 documento aprovado por (venda, tipo) simultaneamente.

`TIPO_ASSINADO_PARA_GERADO = {'proposta_assinada': 'proposta', 'contrato_assinado': 'contrato'}`
— mapeia tipo de upload assinado pro tipo de `DocumentoGerado` correspondente.

---

## 4. Estados e Transições

### Lote.situacao × RegisterVenda.tipo_venda

```
DISPONIVEL
  → (ReservaTemporariaView.get)      EM_RESERVA          [lock 30 min, sem RegisterVenda ainda]
  → (ReservaTemporariaView.form_valid) PRE-RESERVA        [lote.tempo_reservado = agora + tempo_reserva do empreendimento]

PRE-RESERVA / EM_RESERVA
  → (CriarReservadoView.form_valid, sem desconto) RESERVADO   + RegisterVenda.tipo_venda=RESERVADO, is_ativo=True
  → (CriarReservadoView.form_valid, com desconto) ANALISE     + RegisterVenda.tipo_venda=ANALISE,   is_ativo=True

ANALISE
  → (AceitaReservaView)  RESERVADO   + tipo_venda=RESERVADO, is_ativo=True, aceite_proposta=user
  → (CancelarAceiteReservaView)  PRE-RESERVA + tipo_venda='NAO_ACEITE' (⚠️ ver §10 — valor não bate com TypeVenda.NAO_ACEITE)

RESERVADO
  → (CriarVendaView, exige proposta+contrato aprovados com lastro + checklist doc cliente completo) PRE-VENDA
       lote.situacao='PRE-VENDA', venda.tipo_venda='PRE-VENDA'
  → (CancelarReservaView) DISPONIVEL + tipo_venda=CANCELADA, is_ativo=False (arquiva docs vigentes)
  → (CancelarVendaView)   DISPONIVEL + tipo_venda=CANCELADA, is_ativo=False
  → (RenovaReservaView)   sem mudança de estado, só estende dt_reserva

PRE-VENDA
  → (EfetivarVendaView, só ADMINISTRADOR, exige mesmos gates de CriarVendaView) VENDIDO
       lote.situacao='VENDIDO', venda.tipo_venda='VENDIDO', dt_venda=hoje

qualquer estado com reg_venda
  → (CancelarReservadoCadastroView, opera por lote_uuid) DISPONIVEL + tipo_venda=CANCELADA (sem checar is_ativo/gates)
```

### VendaDocumento.status
`enviado` (default no upload) → `aprovado` (admin aprova, arquiva outros aprovados do mesmo tipo)
/ `rejeitado` (admin rejeita) → `arquivado` (ao cancelar a venda, ou ciclo antigo).

---

## 5. Views

Todas exigem `has_permission_decorator` (django-role-permissions) exceto onde indicado.

| Rota | View | Método | O que faz |
|---|---|---|---|
| `insert_venda/<uuid:venda_uuid>/` | `CriarVendaView` | POST | RESERVADO → PRE-VENDA (gate documentos) |
| `insert_reserva/<uuid:reserva_uuid>/` | `CriarReservadoView` | GET/POST | form de reserva, cria/atualiza RegisterVenda, calcula RESERVADO vs ANALISE |
| `reservado/<uuid:lote_uuid>/` | `ReservadoView` | GET | detalhe de reserva (template `reservado.html`) |
| `reservado_detalhes/<uuid:reserva_uuid>/` | `ReservadoDetalheView` | GET | detalhe completo, controle de acesso (admin vê tudo, user só o próprio) |
| `reserva_temporario/<uuid:lote_uuid>/` | `ReservaTemporariaView` | GET/POST | lock temporário de 30min → pré-reserva |
| `select/<uuid:venda_uuid>/`, `renova_reserva/<uuid:venda_uuid>/` | `RenovaReservaView` | POST | estende `dt_reserva` |
| `aceita_analise/<uuid:reserva_uuid>/` | `AceitaReservaView` | POST | ANALISE → RESERVADO |
| `analise/<uuid:lote_uuid>/` | `AnaliseView` | GET | tela de análise de desconto |
| `listar_venda_relatorio/` | `ListarendaRelatorioView` | GET | lista paginada, todas as vendas, filtros por texto/tipo |
| `listar_reserva/` | `RelatorioReservaView` | GET | lista só `RESERVADO`+`is_ativo=True`, filtros |
| `listar_analise/` | `ListasAnalisesView` | GET | lista `ANALISE`, template Tailwind |
| `listar_venda/` | `ListaVendaView` | GET | lista `is_ativo=True`, filtros (ver bug §10) |
| `venda_delete/<uuid:delete_uuid>/` | `CancelarVendaView` | POST | venda → CANCELADA |
| `reservado_cancelada_cadastro/<uuid:cancelaReserva_uuid>/` | `CancelarReservadoCadastroView` | POST | cancela por lote_uuid, sem checar is_ativo |
| `reservado_delete_lista/`, `reservado_delete/<uuid:reserva_uuid>/` | `CancelarReservaView` | POST | RESERVADO/ANALISE → CANCELADA, arquiva docs |
| `reservado_delete_aceite/<uuid:reserva_uuid>/` | `CancelarAceiteReservaView` | POST | ANALISE → NAO_ACEITE |
| `pre-venda/<uuid:venda_uuid>/` | `PreVendaDetalheView` | GET | só ADMINISTRADOR |
| `efetivar-venda/<uuid:venda_uuid>/` | `EfetivarVendaView` | POST | PRE-VENDA → VENDIDO, só ADMINISTRADOR |
| `venda/<uuid:venda_uuid>/documento/upload/` | `VendaDocumentoUploadView` | POST | upload de proposta/contrato assinado; CORRETOR só na própria venda |
| `venda/documento/<uuid:doc_uuid>/aprovar/` | `VendaDocumentoAprovarView` | POST | só ADMINISTRADOR, arquiva aprovados anteriores do mesmo tipo |
| `venda/documento/<uuid:doc_uuid>/rejeitar/` | `VendaDocumentoRejeitarView` | POST | só ADMINISTRADOR |

---

## 6. Regras de Negócio Implementadas

- **Gate de pré-venda** (`create_views.py:85-113`): exige proposta assinada aprovada **com lastro**
  (`documento_gerado` não nulo) + contrato assinado aprovado com lastro + checklist de documentos
  do cliente 100% completo. Mesmo gate reaplicado na efetivação (`create_views.py:43-63`).
- **Checklist de documentos do cliente** (`services.py:7-57`): regra PF usa CNH OU RG_NOVO OU
  (RG+CPF) em ordem de preferência; sempre exige COMPROVANTE_RESIDENCIA pro titular, e
  COMPROVANTE_ESTADO_CIVIL se casado; cônjuge segue a mesma regra via `pertence_a='CONJUGE'`.
  PJ exige CNPJ, CONTRATO_SOCIAL, RG_CPF_ADMINISTRADOR, COMPROVANTE_RESIDENCIA.
- **Reserva com desconto vira análise** (`create_views.py:466-493`): se `valor_desconto > 0`,
  `tipo_venda='ANALISE'` em vez de `RESERVADO` — precisa de aceite manual (`AceitaReservaView`).
- **Bloqueio de reserva duplicada** (`create_views.py:385-415`): não deixa criar nova reserva se já
  existe uma ativa (`tipo_venda not in ['CANCELADA', 'NAO_ACEITE']` — string com underscore, ver §10).
- **Cálculo de valor financiado** (`forms.py:386-404`): `total - desconto - entrada` — **não subtrai
  o sinal**, mesmo o sinal sendo capturado e validado no form (débito conhecido, ver §10).
- **Documento com lastro** (`create_views.py:24-27`): só considera "aprovado válido" se o
  `VendaDocumento` tiver `documento_gerado` vinculado (gerado pelo sistema, não só um upload avulso).
- **Um único documento aprovado por tipo** (`models.py:147-153`): garantido a nível de banco por
  constraint; ao aprovar um novo, o anterior do mesmo tipo é arquivado automaticamente
  (`detail_views.py:440-442`).
- **Controle de acesso em `ReservadoDetalheView`** (`detail_views.py:178-202`): ADMINISTRADOR vê
  qualquer reserva; usuário comum só vê reserva onde `user=self.request.user`; sem sessão ou sem
  reserva correspondente cai em página pública `permissaoVenda.html`.
- **Upload restrito ao corretor dono da venda** (`detail_views.py:392-396`): `CORRETOR` só faz
  upload se `venda.corretor == request.user`; senão 404 (não 403 — oculta a existência da venda).

---

## 7. Services e Signals

- `vendas/signal.py` — **vazio**, nenhum signal registrado no módulo.
- `vendas/services.py`:
  - `checklist_documentos_cliente(cliente)` — usado por `PreVendaDetalheView`, `CriarVendaView`,
    `EfetivarVendaView`, `ReservadoView`, `ReservadoDetalheView`. Única fonte da regra (comentário
    no código pede explicitamente pra não duplicar).
  - `documento_gerado_mais_recente(venda, tipo_assinado)` — usado no auto-link do upload
    (`VendaDocumentoUploadView`) e no backfill (`vincular_documentos_pendentes`).

---

## 8. Templates

| Template | Uso | Stack |
|---|---|---|
| `reserva.html` | form de `CriarReservadoView` | Bootstrap/AdminLTE |
| `reservado.html` | `ReservadoView` | Bootstrap/AdminLTE |
| `reservado_detalhe.html` | `ReservadoDetalheView` | Bootstrap/AdminLTE — **742 linhas**, tem bug cross-app (ver §10) |
| `reserva-temporaria-vendas.html` | `ReservaTemporariaView` | Bootstrap/AdminLTE |
| `analisa.html` | `AnaliseView` | Bootstrap/AdminLTE |
| `permissaoVenda.html` | página pública de acesso negado | Bootstrap/AdminLTE |
| `update_reserva.html` | não referenciado em nenhuma view atual (verificar uso) | Bootstrap/AdminLTE |
| `venda.html` | não referenciado em nenhuma view atual (verificar uso) | Bootstrap/AdminLTE |
| `lote_vendido_sem_venda.html` | não referenciado em nenhuma view atual (verificar uso) | Bootstrap/AdminLTE |
| `lista_venda.html` | `ListaVendaView` | Bootstrap/AdminLTE |
| `lista_venda_relatorio.html` | `ListarendaRelatorioView` | Bootstrap/AdminLTE |
| `lista_reserva.html` | `RelatorioReservaView` | Bootstrap/AdminLTE |
| `lista_analise.html` | `ListasAnalisesView` | **Tailwind** (`glot-*`, já migrado) |
| `vendas/pre_venda_detalhe.html` | `PreVendaDetalheView` | Bootstrap/AdminLTE |
| `papeis/venda_proposta.html`, `papeis/venda_contrato.html` | templates de impressão A4 (usados pelo módulo `documentos` na geração) | CSS print dedicado |

`lista_analise.html` é a única tela do módulo já em Tailwind — resto segue Bootstrap/AdminLTE,
conforme estado do projeto (migração gradual, não expandir sem autorização).

---

## 9. Cobertura de Testes

4207 linhas de teste (pytest, fixtures em `conftest.py`).

| Arquivo | Cobre |
|---|---|
| `test_create_views.py` | `CriarVendaView`, `EfetivarVendaView` |
| `test_delete_views.py` | `CancelarReservaView` (só essa) |
| `test_detail_views.py` | `ReservadoView`, `AnaliseView`, `ReservadoDetalheView`, `PreVendaDetalheView`, `VendaDocumentoUploadView`, `VendaDocumentoAprovarView`, `VendaDocumentoRejeitarView` (arquivo maior, 782 linhas) |
| `test_list_views.py` | `ListaVendaView` (só essa) |
| `test_management_commands.py` | os 2 management commands, cenários de relatório/auto-vincular/dry-run |
| `test_models.py` | `RegisterVenda.__str__`, `VendaDocumento` |

**Sem teste dedicado:**
- `CriarReservadoView` (fluxo central de reserva/análise, inclusive Task 6 SDD) — confirmado, sem
  `class TestCriarReservadoView` em nenhum arquivo.
- `CancelarVendaView`, `CancelarReservadoCadastroView`, `CancelarAceiteReservaView`.
- `RenovaReservaView`, `AceitaReservaView`, `ReservaTemporariaView`.
- `ListarendaRelatorioView`, `RelatorioReservaView`, `ListasAnalisesView` (só `ListaVendaView` tem
  teste entre as 4 list views).
- `RegisterVendaForm` (cálculos monetários, `_calcular_valor_financiado`, `_parse_money`) sem teste
  unitário direto — só indiretamente via `test_create_views.py`.

---

## 10. Débitos Técnicos e Achados

1. **`valor_total` calculado mas nunca persistido** — `forms.py:345-347` faz
   `instance.valor_total = self._calcular_valor_total()`, mas `RegisterVenda` **não tem campo
   `valor_total`** (`models.py` só tem `valor_inicio_contrato`, `valor_financiado`, etc.). Django
   aceita o `setattr` silenciosamente (não é campo do model) e o valor é perdido — nunca vai pro
   banco. `valor_inicio_contrato` (que seria o campo certo pro "valor do contrato") nunca é setado
   em lugar nenhum do form ou das views. Confirma o débito já registrado em memória
   (`project_registervenda_valores`) — ainda presente.

2. **`valor_sinal` ignorado no cálculo do financiado** — `forms.py:386-404`,
   `_calcular_valor_financiado()` faz `total - desconto - entrada`, sem subtrair `sinal` mesmo o
   sinal sendo capturado, validado e salvo no mesmo form. Resultado: `valor_financiado` fica maior
   do que deveria quando há sinal informado. Confirma débito já registrado em auditoria anterior.

3. **`NAO_ACEITE` gravado com valor divergente do `TextChoices`** —
   `models.py:27` define `TypeVenda.NAO_ACEITE = 'NAO-ACEITE'` (hífen), mas
   `delete_views.py:103` (`CancelarAceiteReservaView`) grava `venda.tipo_venda = 'NAO_ACEITE'`
   (underscore) e `create_views.py:391` (`CriarReservadoView.form_valid`) checa contra o mesmo
   valor com underscore. Escrita e leitura são internamente consistentes entre si, mas **nenhuma
   delas bate com `TypeVenda.NAO_ACEITE`** — filtrar por `tipo_venda=TypeVenda.NAO_ACEITE` no
   admin, relatórios ou `ListaVendaView.filtros['tipo_venda']` nunca vai encontrar essas linhas.
   Confirma débito já registrado em memória — ainda presente.

4. **`ListaVendaView` — filtro `is_ativo=True` fixo** — `list_views.py:145`
   (`super().get_queryset().filter(is_ativo=True)`). Cruzado com o achado #3: vendas com
   `tipo_venda='NAO_ACEITE'` têm `is_ativo=False` (setado em `delete_views.py:102`), então nem
   aparecem aqui de qualquer forma — mas o filtro em si (só ativos) exclui também `CANCELADA` e
   `VENDIDO`? Não — `CancelarVendaView`/`CancelarReservaView` também setam `is_ativo=False` ao
   cancelar, então cancelamentos desaparecem da listagem "venda" por completo, e `EfetivarVendaView`
   (VENDIDO) **não mexe em `is_ativo`** — permanece o que já estava (`True`, herdado do estado
   RESERVADO/PRE-VENDA anterior), então vendas efetivadas aparecem. Semântica do filtro é
   inconsistente com o nome da tela ("lista de vendas" deveria plausivelmente incluir histórico de
   canceladas). Já registrado como débito em memória.

5. **`urls_old.py` código morto e quebrado** — importa só `CriarReservadoView` (não usado no
   arquivo) e referencia `views.criarVenda` / `views.cancelarReservado`
   (`vendas/urls_old.py:8,12`) — **`views` nunca é importado no arquivo**, então até carregar essa
   URLconf (se algum lugar apontasse pra ela) daria `NameError`. Não está registrada em nenhum
   `include()` ativo (confirmar antes de deletar — já listado como limpeza pendente em
   `CLAUDE.local.md`).

6. **Templates órfãos** — `update_reserva.html`, `venda.html`, `lote_vendido_sem_venda.html` não
   aparecem como `template_name` em nenhuma view atual do módulo (buscar também em outros apps
   antes de considerar morto — pode ser incluído via `render()` direto ou de outro app).

7. **`ReservaTemporariaView.form_valid` atribui string a campo que parece ser FK** —
   `create_views.py:672-673`: `lote.user = self.request.user.first_name` e
   `lote.telefone_user = self.request.user.contato`. Se `Lote.user` for FK pra `User` (não
   verificado neste mapeamento, ver `empreendimentos/models.py`), isso quebraria; se for CharField
   de texto solto, é só um dado semanticamente estranho (nome, não referência). Necessário
   confirmar o tipo do campo em `empreendimentos.models.Lote` antes de tratar como bug.

8. **Mojibake generalizado** — `create_views.py` e `forms.py` têm dezenas de comentários e strings
   de mensagem de erro corrompidos (`"PRÃ‰ RESERVA"`, `"nÃƒÆ’Ã‚Â£o pode ser negativo"`,
   `"CONFIGURAÃƒÆ’Ã¢â‚¬Â¡ÃƒÆ’Ã†â€™O"`). Cosmético em comentários, mas **as mensagens de erro do form
   ficam ilegíveis pro usuário final** (ex.: `forms.py:248-250`, `284-286`, `320-322`) — isso é
   além do débito "mojibake em comentários" já registrado em memória (esse é sobre
   `create_views.py`), pois aqui afeta strings visíveis ao usuário.

9. **`CancelarReservadoCadastroView` sem verificação de `is_ativo` ou de dono** —
   `delete_views.py:43-59`: cancela qualquer `reg_venda` vinculado ao lote informado por UUID,
   sem checar se a venda já estava inativa/cancelada, nem ownership além da
   `has_permission_decorator`. Rota redundante com `CancelarReservaView`/`CancelarVendaView` (3
   views fazendo cancelamento por caminhos ligeiramente diferentes) — candidato a consolidação,
   fora do escopo deste mapeamento.

10. **`RegisterVendaIntercalada.valor_intercalada` é CharField** — `models.py:92`, enquanto todo o
    resto dos campos monetários do módulo já foi migrado pra `DecimalField` (migration `0062`).
    Model parece não usado em nenhuma view (só aparece no admin como inline) — confirmar se é
    feature morta antes de migrar o tipo.

11. **Confirmado ainda válido**: bug pré-existente cross-app em
    `vendas/templates/reservado_detalhe.html:742` — `{% url 'documentos:documento-pdf' %}`
    referencia rota inexistente na URLconf ativa de `documentos` (só existe a view morta em
    `views_documentos.py`, nunca registrada). Quebra com `NoReverseMatch` se
    `proposta_disponivel` for truthy no contexto (`detail_views.py:291-294` sempre calcula esse
    valor). Não é bug do módulo `vendas` em si, mas o template dele é o gatilho.

---

## 11. Migrations — Histórico Estrutural Relevante

67 migrations no total; a maioria (`0002`–`0030`) são ajustes incrementais de `dt_reserva` e
campos relacionados, sem interesse arquitetural isolado. Marcos relevantes:

| Migration | Mudança |
|---|---|
| `0031`–`0032`, `0054`, `0057` | ajustes sucessivos em `tipo_venda` (choices) |
| `0036`–`0038` | model `Contrato` criado e **removido** na sequência seguinte (feature abandonada) |
| `0040` | remove campo com typo `valor_dinanciado` (era `valor_financiado` grafado errado) |
| `0041`–`0043` | adiciona `uuid` em `RegisterVenda` (pré-migração IDOR desta sessão — já existia) |
| `0044` | adiciona FK `corretor` |
| `0045`–`0046` | `valor_inicio_contrato`, `RegisterVendaIntercalada`, `valor_entrada` |
| `0049`–`0050` | ajustes em `valor_financiado` |
| `0056` | remove/recria campo `desconto` |
| `0060` | adiciona `corretor_nome` (snapshot de texto) |
| `0061` | **rename `TypeLote` → `TypeVenda`**, adiciona choice `PRE-VENDA` (Task 4 do plano SDD vendas) |
| `0062` | **converte campos financeiros de CharField → DecimalField** (Task 5 do plano SDD vendas) |
| `0063` | cria model `VendaDocumento` |
| `0064` | adiciona campo `ciclo` em `VendaDocumento` (histórico de idas e vindas) |
| `0065` | `UniqueConstraint unico_aprovado_por_venda_tipo` — precisou do management command
`arquivar_documentos_duplicados` rodando antes em produção pra não falhar |
| `0066` | adiciona validador de extensão/tamanho em `arquivo_assinado` (fix de segurança
mencionado em `CLAUDE.local.md` — commit feito por engano por um fork numa sessão anterior, mas
o conteúdo é correto) |
| `0067` | adiciona `uuid` em `VendaDocumento` (Fase 2 da migração IDOR desta sessão) |

---

## 12. Pendências / Próximos Passos

Já registradas em `CLAUDE.local.md` e nas memórias do projeto, reconfirmadas neste mapeamento:

- Corrigir `valor_sinal` ignorado em `_calcular_valor_financiado` (achado #2).
- Decidir o que fazer com `valor_total`/`valor_inicio_contrato` nunca persistido (achado #1).
- Corrigir valor de `NAO_ACEITE` pra bater com `TypeVenda.NAO_ACEITE` (achado #3) — precisa de
  migração de dados se já houver linhas gravadas com o valor errado em produção.
- Revisar semântica do filtro `is_ativo` em `ListaVendaView` (achado #4).
- Confirmar e remover `urls_old.py` (achado #5) — perguntar antes, conforme já anotado.
- Confirmar uso real de `update_reserva.html`, `venda.html`, `lote_vendido_sem_venda.html` antes de
  considerar órfãos (achado #6).
- Escrever testes pra `CriarReservadoView`, `CancelarVendaView`, `CancelarReservadoCadastroView`,
  `CancelarAceiteReservaView`, `RenovaReservaView`, `AceitaReservaView`, `ReservaTemporariaView`,
  `ListarendaRelatorioView`, `RelatorioReservaView`, `ListasAnalisesView` (§9).
- Corrigir bug cross-app em `reservado_detalhe.html:742` (achado #11) — já reportado, fora do
  escopo do módulo `vendas` isoladamente.
- Consolidar as 3 rotas de cancelamento (achado #9) — decisão de produto/arquitetura, não mexer
  sem autorização.