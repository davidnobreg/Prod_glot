# Relatório de Auditoria — GLOT (2026-06-28)

## Resumo executivo

- **Módulos analisados:** 9 (accounts, clientes, cobranca, core, dashboard, documentos, empreendimentos, mensagem, vendas)
- **Total de problemas:** 34 (6 críticos, 9 altos, 10 médios, 9 baixos)
- **Sub-agentes executados:** bugs, quality, security, tests

---

## accounts

### 🔴 Bugs
- [MÉDIO] `logout` view sem `@require_POST` — pode ser acionado via link GET, bypassando proteção CSRF (accounts/views.py:82)
- [BAIXO] `listarUsuario` retorna todos os usuários do sistema sem filtro por empreendimento — potencial vazamento entre corretores

### 🔴 Segurança
- [MÉDIO] `login` view sem rate limiting — suscetível a brute-force de senhas (accounts/views.py:62)
- [BAIXO] `logout` via GET — vetor CSRF para forçar logout de usuário autenticado

### 🔵 Qualidade
- [MÉDIO] `_contexto_vendas_corretor` com lógica de filtragem e paginação embutida na view — candidato a `services.py`
- [BAIXO] `alteraUsuario` mistura GET e POST em um único método sem separação clara

### 🟡 Cobertura de testes
- `accounts/tests.py` existe — cobertura básica presente

---

## clientes

### 🔴 Bugs
- [ALTO] `processar_documentos_pendentes` (tasks.py:19): `except Exception as e` engole erro sem re-raise — falhas silenciosas na tarefa Celery
- [BAIXO] `selectClienteEndereco` com decorator comentado (`# @has_permission_decorator`) mas endpoint registrado — endpoint morto, sempre retorna 404, mas acessível sem autenticação (clientes/views.py:533)

### 🔴 Segurança
- [BAIXO] Mojibake em strings de validação (ex: `"Campo obrigat\xf3rio"`) — textos de erro aparecem corrompidos para o usuário

### 🔵 Qualidade
- [MÉDIO] `clientes/views.py` extenso com múltiplos helpers (`_wizard_validar_finalizacao`, `_normalize_telefones_rich`, etc.) que poderiam estar em `services.py`
- [MÉDIO] `ClienteBaseForm`: `fields = '__all__'` com `exclude` longo — frágil, inclui campos futuros automaticamente

### 🟡 Cobertura de testes
- Boa cobertura: `test_models.py`, `test_views.py`, `test_wizard.py`, `test_integration.py`, `conftest.py`

---

## cobranca

### 🔴 Bugs
- [ALTO] `cliente_id = models.ForeignKey(Cliente, ...)` (cobranca/models.py:12) — Django gera coluna `cliente_id_id` no banco (convenção errada; deve ser `cliente`)
- [ALTO] `valor_do_total = models.CharField(max_length=50)` — valor monetário como string, impossível fazer cálculos ou ordenação
- [MÉDIO] `url_pdf = models.ImageField(...)` para armazenar URL de PDF — semanticamente incorreto; use `FileField` ou `URLField`
- [MÉDIO] `is_ativo = models.BooleanField(default=False)` — boleto começa inativo por padrão; intencional?

### 🔴 Segurança
(nenhum problema encontrado)

### 🔵 Qualidade
- [ALTO] `cobranca/views.py` e `cobranca/services.py` completamente vazios — módulo de cobrança sem implementação, mas registrado como app
- [BAIXO] Nomenclatura mista: campos em português (`nosso_numero`, `cod_barras`) e inglês (`is_ativo`, `created_at`)

### 🟡 Cobertura de testes
- `cobranca/tests.py` existe, mas módulo não está implementado

---

## core

### 🔴 Bugs
(nenhum problema encontrado)

### 🔴 Segurança
- [BAIXO] `SECRET_KEY`, tokens e credenciais carregados via `decouple` — OK. Sem credenciais hardcoded detectadas.

### 🔵 Qualidade
- [MÉDIO] Celery sem queue dedicada para `vendas.*` e `documentos.*` — tarefas de PDF pesado e liberação de reservas compartilham fila default com tarefas leves
- [BAIXO] `TEMPO_RESERVA_MINUTOS = 10` em settings.py sem uso detectado no código

### 🟡 Cobertura de testes
- Sem arquivo de testes para `core/` — settings, celery e decorators não testados

---

## dashboard

### 🔴 Bugs
- [CRÍTICO] `vendas_ativas = vendas.filter(is_ativo=False)` (dashboard/views.py:22) — filtra registros **inativos** como "ativos"; todas as métricas do dashboard estão baseadas em dados invertidos

### 🔴 Segurança
- [ALTO] `DashboardView` sem `LoginRequiredMixin` — qualquer usuário não autenticado pode acessar o painel principal e ver métricas de vendas

### 🔵 Qualidade
- [MÉDIO] `get_resumo_empreendimentos` executa múltiplos `Count()` com `distinct=True` — pode ser lenta em bases com muitos lotes
- [BAIXO] `formatar_moeda` duplicada localmente no método (também existe em `core/utils.py`)

### 🟡 Cobertura de testes
- `dashboard/tests.py` existe

---

## documentos

### 🔴 Bugs
- [MÉDIO] `gerar_pdf_documento` task (tasks.py:99): em falha com retries pendentes, reseta `status` para `RASCUNHO` — confunde o usuário que vê o documento "voltar" ao rascunho durante o processamento

### 🔴 Segurança
- [ALTO] `_renderizar_documento` (documentos/views.py:901): usa `Template(documento.texto).render(Context(contexto))` com engine **não restrito** do Django — se conteúdo de `CadastroDocumento.texto` contiver `{% load os %}` ou tags arbitrárias, há risco de SSTI. O `_engine_seguro` em `services.py` mitiga o caminho novo, mas o caminho legado (`proposta_legado`) usa a engine padrão.
- [MÉDIO] `autoescape=False` no `_engine_seguro` (services.py) — conteúdo HTML não é escapado; XSS se variáveis contiverem HTML malicioso

### 🔵 Qualidade
- [BAIXO] `documentos/services.py` bem estruturado, mas muito extenso — considerar separar `construir_contexto_*` em módulo próprio

### 🟡 Cobertura de testes
- `test_models.py` e `test_services.py` presentes — boa cobertura do módulo novo

---

## empreendimentos

### 🔴 Bugs
- [ALTO] `deleteEmpreendimento` (views.py): usa `Empreendimento.objects.get(id=...)` sem `get_object_or_404` — retorna HTTP 500 se empreendimento não existe
- [MÉDIO] `Lote.cliente_reserva = models.CharField(default=0)` — default numérico em campo string; `default=''` seria correto
- [MÉDIO] `Lote.user = models.CharField(max_length=100, default=0)` — mesmo problema
- [MÉDIO] `Lote.telefone` e `Lote.telefone_user` sem `blank=True` — campos obrigatórios pelo modelo mas populados manualmente no código sem validação

### 🔴 Segurança
- [MÉDIO] Nenhuma verificação de ownership nos lotes — qualquer usuário autenticado com permissão `listaQuadra` pode ver dados de qualquer empreendimento

### 🔵 Qualidade
- [ALTO] `listaQuadra` (views.py): N+1 queries — loop sobre quadras, depois loop sobre lotes dentro; sem `prefetch_related('lotes')` (empreendimentos/views.py)
- [MÉDIO] `formatar_moeda` definida localmente dentro de `listaQuadra` — função utilitária duplicada, deveria usar `core.utils`
- [BAIXO] `listaQuadra` com ~120 linhas — candidato a refatoração com service

### 🟡 Cobertura de testes
- `empreendimentos/tests.py` existe

---

## mensagem

### 🔴 Bugs
- [ALTO] `enviar_mensagem_task` (tasks.py:110): `raise Exception(f"Falha no envio: {resultado}")` não está em `autoretry_for` — falha de envio não dispara retry automático do Celery

### 🔴 Segurança
- [CRÍTICO] `enviar_mensagem_view` com `@csrf_exempt` e **sem `@login_required`** (mensagem/views.py:5) — endpoint público sem autenticação que dispara mensagens WhatsApp via n8n; qualquer pessoa na internet pode abusar

### 🔵 Qualidade
- [BAIXO] `mensagem/models.py` completamente vazio — arquivo desnecessário
- [BAIXO] Endpoint exposto pode ser usado para spam de WhatsApp em massa se descoberto

### 🟡 Cobertura de testes
- `mensagem/tests.py` existe, mas endpoint crítico não validado

---

## vendas

### 🔴 Bugs
- [CRÍTICO] `RegisterVenda.__str__` (models.py:60): acessa `self.lote.quadra.namequadra` sem verificar se `lote` é `None` — `lote` é `OneToOneField(null=True)`, crash garantido no Django Admin quando lote é nulo
- [CRÍTICO] `CriarReservadoView.get()` (create_views.py): executa `lote.save()` em requisição GET — mutation de banco em GET viola HTTP semantics e cria side effects em recarregamentos de página
- [ALTO] `liberar_lotes_reservados_expirados` (tasks.py:168): `except Exception as e` sem re-raise dentro do loop — erros individuais são logados mas não propagados; task sempre reporta sucesso
- [MÉDIO] `lote.save()` na task sem `update_fields=['situacao', 'cliente_reserva', 'telefone']` — salva todos os campos, sobrescrevendo mudanças concorrentes

### 🔴 Segurança
- [ALTO] `CriarVendaView` sem verificação de ownership (create_views.py:23) — qualquer usuário com permissão `criarVenda` pode finalizar a venda de qualquer lote de qualquer empreendimento
- [MÉDIO] `CriarReservadoView.form_valid`: `reserva.tipo_venda = 'ANALISE'` hardcoded — o bloco condicional que verificava desconto para definir `RESERVADO` vs `ANALISE` foi removido/comentado; todas as reservas vão para ANALISE

### 🔵 Qualidade
- [ALTO] `create_views.py`: formatação extremamente vertical (cada expressão em linha separada) — arquivo dificílimo de ler e revisar
- [MÉDIO] `RegisterVendaIntercalada.valor_intercalada = models.CharField(...)` — valor monetário como string
- [BAIXO] `valor_financiado = models.DecimalField(max_digits=50, ...)` — `max_digits=50` absurdamente alto para valor financeiro

### 🟡 Cobertura de testes
- [CRÍTICO] Apenas `vendas/tests.py` (arquivo único genérico) para o módulo mais crítico do sistema — views de reserva, cancelamento, análise e finalização de venda sem testes dedicados

---

## Pendências prioritárias (top 10)

| # | Severidade | Módulo | Problema |
|---|-----------|--------|---------|
| 1 | 🔴 CRÍTICO | mensagem | `enviar_mensagem_view` sem autenticação + `@csrf_exempt` — endpoint público dispara WhatsApp |
| 2 | 🔴 CRÍTICO | dashboard | `is_ativo=False` filtra inativos como "ativos" — métricas do dashboard completamente erradas |
| 3 | 🔴 CRÍTICO | vendas | `RegisterVenda.__str__` acessa `lote.quadra` sem checar `None` — crash no Admin |
| 4 | 🔴 CRÍTICO | vendas | `CriarReservadoView.get()` executa `lote.save()` em requisição GET |
| 5 | 🟠 ALTO | dashboard | `DashboardView` sem `LoginRequiredMixin` — painel acessível sem login |
| 6 | 🟠 ALTO | documentos | `Template(documento.texto).render()` com engine irrestrito no caminho legado — risco SSTI |
| 7 | 🟠 ALTO | vendas | `CriarVendaView` sem verificação de ownership — qualquer corretor finaliza qualquer venda |
| 8 | 🟠 ALTO | cobranca | `cliente_id = models.ForeignKey(...)` gera coluna `cliente_id_id` no banco |
| 9 | 🟠 ALTO | empreendimentos | N+1 queries em `listaQuadra` — loop sobre quadras sem `prefetch_related` |
| 10 | 🟠 ALTO | vendas | `liberar_lotes_reservados_expirados` engole exceções — task reporta sucesso mesmo com falhas |

---

*Gerado automaticamente por audit-code em 2026-06-28*
