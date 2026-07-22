# Módulo: cobranca

> Mapeamento do estado atual do código. Documenta o que existe — não é proposta de mudança.
> Gerado em 2026-07-21.

---

## 1. Visão Geral

App responsável pela cobrança financeira de uma venda: gera carnês de parcelas (ou entrada
avulsa), registra baixa manual de pagamento e guarda a configuração de gateway bancário por
empreendimento (credenciais criptografadas em repouso). Depende de `vendas` (`RegisterVenda`),
`empreendimentos` (`Empreendimento`) e `accounts` (`User`).

**Fase 1 apenas.** Não há integração real com banco ainda — `webhook.py` e `serializers.py`
existem como arquivos vazios (scaffold da Fase 2, sem uso hoje). O módulo hoje cobre só o
controle interno de parcelas e baixa manual; emissão de boleto de fato (Sicredi/outros) é
trabalho futuro (ver skill `sicredi-cobranca-api` já disponível no projeto).

---

## 2. Estrutura de Arquivos

```
cobranca/
  models.py                 200 linhas — ConfiguracaoGateway, Carne, Parcela, CobrancaBancaria
  fields.py                  41 linhas — EncryptedCharField/EncryptedTextField (Fernet custom)
  services.py                67 linhas — gerar_carne, gerar_entrada, registrar_baixa_manual
  views.py                  235 linhas — 6 CBVs (django.views.View puro, sem Mixin de permissão)
  urls.py                    19 linhas — 6 rotas, todas uuid
  admin.py                   27 linhas — 4 ModelAdmin
  serializers.py              0 linhas — vazio, scaffold não usado (Fase 2)
  webhook.py                  0 linhas — vazio, scaffold não usado (Fase 2)
  apps.py                     6 linhas
  tests/
    test_services.py        227 linhas
    test_views.py            190 linhas
  templates/cobranca/         6 arquivos .html (ver §8)
  migrations/                 1 arquivo — 0001, cria as 4 tabelas de uma vez
```

---

## 3. Models (`cobranca/models.py`)

### `ConfiguracaoGateway`

Credenciais de integração bancária por empreendimento (1:1).

| Campo | Tipo | Observação |
|---|---|---|
| `uuid` | UUIDField | chave pública |
| `empreendimento` | OneToOne → `empreendimentos.Empreendimento` | `CASCADE`, `related_name='configuracao_gateway'` |
| `gateway` | CharField(choices) | `banco_brasil`/`sicredi`/`sicoob`/`bradesco`/`banco_nordeste`/`caixa_economica` |
| `client_id`, `client_secret`, `convenio` | `EncryptedCharField` | criptografados em repouso (Fernet, ver `fields.py`) |
| `certificado`, `chave_certificado` | `EncryptedTextField` | idem, campo texto livre (sem validação de formato) |
| `sandbox` | BooleanField(default=`True`) | — |

### `Carne`

Agrupador de parcelas mensais de uma venda.

| Campo | Tipo | Observação |
|---|---|---|
| `venda` | FK → `vendas.RegisterVenda` | `PROTECT`, `related_name='carnes'` |
| `numero_carne` | PositiveIntegerField | sequencial por venda (não por empreendimento) |
| `status` | CharField(choices) | `GERADO`/`ENVIADO`/`CANCELADO` — só `GERADO` é alcançado por código atual (ver §4) |
| `ano_referencia` | PositiveIntegerField | — |
| `gerado_por` | FK → `User` | `PROTECT` |

`Meta.unique_together = [('venda', 'numero_carne')]`.

### `Parcela`

Uma parcela de carnê, ou uma entrada avulsa (`carne=None`).

| Campo | Tipo | Observação |
|---|---|---|
| `carne` | FK → `Carne` | `PROTECT`, `null=True` — nulo só para `tipo='ENTRADA'` |
| `venda` | FK → `RegisterVenda` | `PROTECT` |
| `tipo` | CharField(choices) | `ENTRADA`/`PARCELA` |
| `modalidade` | CharField(choices) | `BOLETO`/`MANUAL` |
| `valor`, `valor_pago` | DecimalField(12,2) | `valor_pago` só setado na baixa |
| `data_vencimento`, `data_pagamento` | DateField | — |
| `igpm_aplicado` | DecimalField(8,4), nullable | existe no model, **nunca calculado/preenchido por nenhum código atual** (ver §10) |
| `status` | CharField(choices) | `PENDENTE`/`ENVIADA_BANCO`/`PAGA`/`CANCELADA`/`INADIMPLENTE` — só `PENDENTE`→`PAGA` implementado (ver §4) |
| `baixado_por` | FK → `User`, nullable | preenchido em `registrar_baixa_manual` |

`Meta.unique_together = [('carne', 'numero_parcela')]`.

### `CobrancaBancaria`

Registro de emissão bancária real de uma parcela (1 parcela pode ter N linhas — reemissões —,
`ativa` distingue a vigente das antigas).

| Campo | Tipo | Observação |
|---|---|---|
| `parcela` | FK → `Parcela` | `PROTECT`, `related_name='cobrancas_bancarias'` |
| `ativa` | BooleanField(default=`True`) | — |
| `nosso_numero`, `linha_digitavel`, `codigo_barras`, `url_boleto` | campos de retorno de gateway | — |
| `resposta_banco` | JSONField, nullable | payload bruto da API do banco |
| `erro_mensagem` | TextField, nullable | — |
| `status` | CharField(choices) | `PENDENTE`/`REGISTRADA`/`PAGA`/`CANCELADA`/`ERRO` |

**Nenhuma view ou service do módulo cria uma linha de `CobrancaBancaria` hoje** — o model existe
pronto para a Fase 2 (emissão real de boleto), mas está completamente desconectado do fluxo
atual (§10 achado #3).

---

## 4. Estados e Transições

### `Carne.status`

```
GERADO (único valor setado, em gerar_carne)
```
`ENVIADO`/`CANCELADO` são choices válidas no model, mas nenhum código atual as produz — dependem
da integração bancária real (Fase 2).

### `Parcela.status`

```
PENDENTE (default, em gerar_carne/gerar_entrada)
  → (registrar_baixa_manual, se status in PENDENTE/INADIMPLENTE) PAGA
```
`ENVIADA_BANCO`, `CANCELADA`, `INADIMPLENTE` são choices válidas, mas **nenhuma rotina do sistema
as atribui** — não existe cron/management command de inadimplência, nem cancelamento de
carnê/parcela implementado.

### `CobrancaBancaria.status`

Default `PENDENTE`; como o model nunca é instanciado (§3), nenhuma transição ocorre na prática.

---

## 5. Views (`cobranca/views.py`)

Todas herdam só `LoginRequiredMixin` + `django.views.View` puro — **nenhuma usa
`has_permission_decorator`/django-role-permissions**, padrão usado no resto do projeto.
Controle de acesso é feito via helper local `_somente_administrador(request)`
(`getattr(request.user, 'tipo_usuario', None) == 'ADMINISTRADOR'`), repetido em cada view
(ver §10 achado #1).

| Rota | View | Método | O que faz |
|---|---|---|---|
| `cobranca/venda/<uuid:venda_uuid>/carnes/` | `ListaCarnesVendaView` | GET | lista carnês + entradas da venda |
| `cobranca/venda/<uuid:venda_uuid>/gerar-carne/` | `GerarCarneView` | GET/POST | form de geração; GET pré-preenche `valor_parcela`/`data_primeira_parcela` com dados da venda (`venda.valor_parcela`, `venda.dt_primeira_parcela`) |
| `cobranca/venda/<uuid:venda_uuid>/gerar-entrada/` | `GerarEntradaView` | GET/POST | cria parcela avulsa tipo `ENTRADA` |
| `cobranca/carne/<uuid:carne_uuid>/` | `DetalheCarneView` | GET | detalhe do carnê + parcelas |
| `cobranca/parcela/<uuid:parcela_uuid>/baixa-manual/` | `BaixaManualParcelaView` | GET/POST | registra pagamento manual |
| `cobranca/parcela/<uuid:parcela_uuid>/` | `DetalheParcelaView` | GET | detalhe da parcela + cobranças bancárias vinculadas |

Acesso a partir de `vendas`: botão "Cobranças" em `reservado.html` (admin-only,
`{% url 'lista_carnes_venda' %}`), adicionado no commit `4c29b92`.

---

## 6. Regras de Negócio Implementadas

- **Limite de 12 parcelas por carnê** (`services.py:10-11`): `gerar_carne` levanta `ValueError`
  se `numero_parcelas > 12`.
- **Numeração sequencial de carnê por venda** (`services.py:13-14`): `Max('numero_carne')` + 1,
  não reaproveita números mesmo que um carnê antigo seja cancelado (não há soft-delete de carnê).
- **Entrada sempre com `carne=None`, `numero_parcela=0`** (`services.py:41-50`).
- **Baixa manual só a partir de `PENDENTE`/`INADIMPLENTE`** (`services.py:55-56`): bloqueia
  reprocessar parcela já `PAGA`/`CANCELADA` — `ValueError` renderizado como mensagem de erro na
  própria página (`views.py:201-211`).
- **Pré-preenchimento do form de carnê com dados da venda** (`views.py:57-61`, commit
  `c8b865d`): `valor_parcela` e `data_primeira_parcela` vêm de `venda.valor_parcela`/
  `venda.dt_primeira_parcela`, mas o admin pode sobrescrever livremente no POST — não há
  validação cruzando o valor informado com o da venda.
- **`ConfiguracaoGatewayForm` nunca reexibe segredo já gravado** (`empreendimentos/forms/
  wizard.py:562-564`): `client_id`/`client_secret`/`convenio`/`certificado`/`chave_certificado`
  sempre chegam vazios no `initial`, mesmo já existindo valor no banco — evita vazar segredo na
  tela, mas também significa que reenviar o form sem preencher esses campos não os apaga (só
  `dados_preenchidos()` decide o que entra no `update_or_create`).
- **`dados_preenchidos()` evita `ConfiguracaoGateway` vazio a cada POST do wizard**
  (`wizard.py:566-580`): `sandbox` é `BooleanField` (sempre presente no `cleaned_data`), então
  não conta sozinho como "preenchido" — só cria/atualiza se houver ao menos 1 outro campo
  não vazio.
- **Draft-copy do wizard de update não copia `configuracao_gateway`** (`update.py:290-294`):
  o draft nasce sem gateway próprio; o form em step4 usa como instância inicial
  `draft.configuracao_gateway or real.configuracao_gateway` (mostra o do real se o draft ainda
  não tiver o seu), mas **sempre salva no draft** (`update_or_create(empreendimento=draft, ...)`,
  linha 318). Na finalização (`update.py:428-439`), os campos são copiados manualmente do
  draft para o real via `update_or_create` campo a campo.

---

## 7. Services e Signals

Não existe `cobranca/signal.py`. Toda a lógica de negócio já está isolada em
`cobranca/services.py` (diferente de `vendas`/`clientes`, onde a extração pra `services.py` é
parcial) — `gerar_carne`, `gerar_entrada`, `registrar_baixa_manual`, todas `@transaction.atomic`.

---

## 8. Templates

| Template | Uso | Stack |
|---|---|---|
| `lista_carnes.html` | `ListaCarnesVendaView` | Bootstrap/AdminLTE |
| `gerar_carne.html` | `GerarCarneView` | Bootstrap/AdminLTE |
| `gerar_entrada.html` | `GerarEntradaView` | Bootstrap/AdminLTE |
| `detalhe_carne.html` | `DetalheCarneView` | Bootstrap/AdminLTE |
| `baixa_manual.html` | `BaixaManualParcelaView` | Bootstrap/AdminLTE |
| `detalhe_parcela.html` | `DetalheParcelaView` | Bootstrap/AdminLTE |

Nenhum template deste app está em Tailwind.

---

## 9. Cobertura de Testes

417 linhas de teste (pytest/Django `TestCase`, sem fixtures compartilhadas em `conftest.py` —
cada `TestCase` monta o próprio `setUp`).

| Arquivo | Cobre |
|---|---|
| `test_services.py` | `gerar_carne` (12 parcelas, datas mensais, limite de 12, numeração sequencial, `unique_together`), `gerar_entrada` (tipo/carne nulo/numero 0), `registrar_baixa_manual` (pendente, inadimplente, paga→erro, cancelada→erro) |
| `test_views.py` | `ListaCarnesVendaView` (200 admin / 302 não-admin), `GerarCarneView` (GET 200, POST cria+redireciona, POST >12 parcelas não cria e reexibe erro), `GerarEntradaView` (POST cria+redireciona), `BaixaManualParcelaView` (POST baixa+redireciona, POST em parcela já paga reexibe erro), `DetalheCarneView`/`DetalheParcelaView` (200 admin) |
| `empreendimentos/tests/test_wizard_gateway.py` | `ConfiguracaoGatewayForm` integrada aos wizards de cadastro/update: cria configuração só se algum campo preenchido, atualiza sem tocar no real até finalizar, mantém valores anteriores quando POST reenvia campos em branco |

**Sem teste dedicado:**
- `ConfiguracaoGateway` — nenhum teste do model em si (round-trip de criptografia via
  `EncryptedCharField`/`EncryptedTextField`, `__str__`).
- `CobrancaBancaria` — sem teste (consistente com o model nunca ser instanciado em código real).
- `admin.py` — sem teste (baixa prioridade, aceitável).
- `DetalheCarneView`/`DetalheParcelaView` para usuário não-administrador (só o caminho 200-admin
  é testado; o redirect 302 do não-admin só é coberto para `ListaCarnesVendaView`).
- `fields.py` (`EncryptedFieldMixin`) — sem teste unitário isolado do comportamento de
  `InvalidToken` (`from_db_value` engolindo silenciosamente valor corrompido/chave trocada).

---

## 10. Débitos Técnicos e Achados

1. **Controle de acesso ad-hoc, fora do padrão do projeto** — `views.py:15-16`
   (`_somente_administrador`), repetido em todas as 6 views, em vez de
   `has_permission_decorator`/django-role-permissions (usado em `vendas`, `clientes`,
   `empreendimentos`). Não existe grupo/permissão `glot_*` dedicada para o módulo — checagem é
   só `tipo_usuario == 'ADMINISTRADOR'` direto no código.

2. **`serializers.py` e `webhook.py` vazios** — scaffold sem uso, DRF nunca conectado
   (mesmo padrão já visto em `clientes.ClienteSerializer`, achado #10 daquele módulo). Confirma
   que o módulo está mesmo em Fase 1: só controle manual/interno, sem integração bancária real.

3. **`CobrancaBancaria` nunca instanciado** — model existe pronto (campos de resposta de
   gateway: `nosso_numero`, `linha_digitavel`, `codigo_barras`, `url_boleto`, `resposta_banco`,
   `erro_mensagem`), mas nenhuma view/service cria uma linha. É a peça central da Fase 2
   (emissão real de boleto) — hoje é só estrutura de banco sem consumidor.

4. **Choices de status inalcançáveis** — `Carne.ENVIADO`/`Carne.CANCELADO`,
   `Parcela.ENVIADA_BANCO`/`Parcela.CANCELADA`/`Parcela.INADIMPLENTE` são valores válidos no
   model mas nenhum código atual os atribui. Não há rotina de inadimplência (parcela vencida e
   não paga não muda de status sozinha) nem fluxo de cancelamento de carnê/parcela.

5. **`igpm_aplicado` nunca calculado** — campo existe em `Parcela` mas nenhum `service` o
   preenche. `Empreendimento.tipo_correcao` (default `'IGPM'`, `empreendimentos/models/
   empreendimento.py:51`) já é configurável desde o wizard de empreendimento, mas não há ponte
   entre esse campo e o cálculo de reajuste de parcela — pendência de fase futura.

6. **Chave de criptografia derivada do `SECRET_KEY` do projeto** — `fields.py:9-11`
   (`hashlib.sha256(settings.SECRET_KEY.encode())`). Rotacionar `SECRET_KEY` em produção
   invalida silenciosamente todos os segredos já gravados em `ConfiguracaoGateway`:
   `from_db_value` (`fields.py:26-32`) captura `InvalidToken` e **retorna o valor cru cifrado**
   sem levantar erro — a credencial simplesmente vira lixo ilegível sem aviso nenhum na tela.
   Risco operacional a documentar antes de qualquer rotação de `SECRET_KEY`.

7. **Sem validação de formato para `certificado`/`chave_certificado`** — `Textarea` livre,
   aceita qualquer string; validação de que é de fato um certificado/chave válida ficaria a
   cargo da integração bancária real (ainda não implementada).

8. **Tratamento de erro inconsistente entre views** — `GerarCarneView`/`BaixaManualParcelaView`
   envolvem a chamada ao service em `try/except ValueError` (`views.py:86-98`, `201-211`);
   `GerarEntradaView.post` (`views.py:137-143`) chama `gerar_entrada` direto, sem try/except —
   hoje inofensivo porque o service não levanta exceção, mas divergente do padrão das outras
   views do mesmo módulo caso `gerar_entrada` ganhe validação futuramente.

9. **`requirements.txt` em UTF-16** — já registrado em memória de projeto; dependência
   `cryptography` usada diretamente por `fields.py` (Fernet), não `django-cryptography`
   (incompatível com Django 5.2 — decisão já tomada na Fase 1, ver commit `a42b82e`).

---

## 11. Migrations

1 migration no total — `0001_cobranca_models_iniciais.py` cria as 4 tabelas do módulo de uma
vez (não incrementalmente como em outros apps). Depende de `empreendimentos.0068` e
`vendas.0073_distrato_venda`.

---

## 12. Pendências / Próximos Passos

- **Fase 2**: implementar emissão bancária real — popular `CobrancaBancaria`, implementar
  `webhook.py` (retorno do banco) e, se necessário, `serializers.py` (API). Referência já
  disponível no projeto: skill `sicredi-cobranca-api`.
- Unificar controle de acesso do módulo com o padrão `has_permission_decorator`/
  django-role-permissions do resto do sistema (achado #1) — criar permissão/grupo dedicado em
  vez de checar `tipo_usuario` direto no código.
- Definir rotina de inadimplência (marcar `Parcela.INADIMPLENTE` quando `data_vencimento` passa
  sem pagamento) — hoje nada faz essa transição; candidato a management command agendado,
  seguindo o padrão já usado em `vendas` (`arquivar_documentos_duplicados`).
- Decidir e implementar o cálculo de `igpm_aplicado`, ligando com
  `Empreendimento.tipo_correcao` (achado #5).
- Escrever testes para `ConfiguracaoGateway`/`EncryptedField` (round-trip de criptografia,
  comportamento com chave trocada) e para `CobrancaBancaria` quando o model passar a ser usado.
- Alertar/documentar processo de rotação de `SECRET_KEY` em produção antes que aconteça
  (achado #6) — hoje quebraria silenciosamente toda credencial de gateway já cadastrada.