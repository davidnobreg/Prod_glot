# Wizard de Update de Empreendimento — Design

## Contexto

Wizard de cadastro (6 steps) funciona em `empreendimentos/views.py` /
`forms.py` / `services.py`. Este spec cobre o wizard de **edição**: mesma
UX/layout, mesma ordem de steps, mas operando sobre um empreendimento já
ativo em vez de criar um novo.

Arquivos novos: `views_update.py`, `forms_update.py` (só se necessário —
maioria dos forms de cadastro é reaproveitável direto).
Não alterar `views.py`, `forms.py`, `models.py`. Não gerar migration.
Não mexer em outro app.

## Arquitetura de persistência — draft-copy

Ao abrir o wizard de update pro empreendimento de `uuid` (URL usa
`<uuid:empreendimento_uuid>` — **não `<int:pk>`**, ver "Correções" abaixo):

1. `_get_or_create_draft(request, empreendimento_uuid)` busca o real
   (`is_ativo=True`) e, se a sessão ainda não aponta pra um draft desse
   real, cria uma cópia `Empreendimento(is_ativo=False)`: todos os campos
   escalares copiados + `logo` copiada via `ContentFile` + dois `Endereco`
   novos (cópias independentes de `endereco_empresa`/`endereco_empreendimento`
   — não reaproveita as FKs do real).
2. Sessão guarda só o ponteiro:
   `request.session['wizard_update'] = {"<uuid-do-real>": {"draft_uuid": "..."}}`.
   Nenhum campo de formulário fica em sessão.
3. Steps 1, 2, 3, 5 leem/escrevem no **draft** (mesmo padrão dos forms de
   cadastro: `instance=draft`). Upload de logo é FileField normal no draft,
   sem gambiarra de sessão.
4. Step 4 (representantes) e documentos (empreendimento + representante)
   agem **direto no real** (`empreendimento=real`), imediato via AJAX —
   mesmo comportamento que o wizard de cadastro já tem pros seus próprios
   endpoints (`wizard_representante_del`, `wizard_rep_doc_upload`, etc),
   só que apontando pro objeto ativo em vez do draft.
5. Step 6 POST "Salvar" — `transaction.atomic()`: copia campos escalares
   draft→real, copia logo (delete do logo antigo do real antes, save do
   novo), atualiza os 2 `Endereco` do real in-place com os valores dos
   `Endereco` do draft (não troca a FK, só os campos). Depois do commit
   (fora do atomic): deleta draft + seus 2 enderecos + seu logo, limpa
   sessão, `messages.success`, redirect `lista-empreendimento-tabela`.
6. Botão "Cancelar" (qualquer step): deleta draft + enderecos + logo do
   draft, limpa sessão, redirect sem tocar no real.

**Draft órfão** (browser fechado sem Salvar/Cancelar): aceito como
limitação, mesmo risco que já existe hoje no wizard de cadastro (nenhum
cleanup existe lá — confirmado, não há precedente). Não implementar
cleanup agora.

## Correções feitas em cima do prompt original do usuário

1. **Template path**: prompt original pedia
   `empreendimentos/templates/empreendimentos/wizard/update/` — esse
   prefixo `empreendimentos/` não existe no projeto (cadastro usa
   `empreendimentos/templates/wizard/`, flat). Usar
   `empreendimentos/templates/wizard/update/`.
2. **`<int:pk>` → `<uuid:empreendimento_uuid>`**: toda `empreendimentos/urls.py`
   hoje é uuid (memória do projeto documenta 6 fases de migração int→uuid,
   `empreendimentos` foi a Fase 1). Rotas novas com `<int:pk>` seriam
   regressão. Todas as views novas buscam por `uuid=`, não `pk=`.
3. **Redirect `listar-empreendimento` não existe** — nome correto é
   `lista-empreendimento-tabela` (`urls.py:83`).
4. **Permissão**: `@has_permission_decorator('criarEmpreendimento')` (usado
   no wizard de cadastro) é semanticamente errado pro update. Usar
   `alterarEmpreendimento` — já existe em `core/roles.py`, é o mesmo usado
   pela view antiga `alteraEmpreendimento`.
5. **Step 5 não tem ModelForm dedicado no cadastro** (`wizard_step5` seta
   campos direto via `request.POST.get()` + `full_clean()`) — update step5
   segue o mesmo padrão direto-no-draft, sem criar `ConfiguracaoStep5Form`
   novo.

## `services.py` — função nova

```python
def _copiar_endereco_draft_para_real(endereco_real, endereco_draft):
    """Atualiza campos do Endereco real com valores do draft. Não cria instância nova."""
    if endereco_draft is None:
        return endereco_real
    campos = ['cep', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'estado']
    if endereco_real is None:
        return criar_ou_atualizar_endereco(
            {c: getattr(endereco_draft, c) for c in campos}
        )
    for campo in campos:
        setattr(endereco_real, campo, getattr(endereco_draft, campo))
    endereco_real.save()
    return endereco_real
```

Todo o resto (`criar_ou_atualizar_endereco`, `criar_representante`,
`atualizar_representante`, `desativar_representante`,
`criar_documento_empreendimento`, `remover_documento_empreendimento`,
`criar_documento_representante`, `remover_documento_representante`) já
existe e é reaproveitado sem alteração.

## URLs — `empreendimentos/urls.py` (adicionar, não alterar existentes)

```python
path('editar/<uuid:empreendimento_uuid>/step1/', views_update.wizard_update_step1, name='empreendimento_update_step1'),
path('editar/<uuid:empreendimento_uuid>/step2/', views_update.wizard_update_step2, name='empreendimento_update_step2'),
path('editar/<uuid:empreendimento_uuid>/step3/', views_update.wizard_update_step3, name='empreendimento_update_step3'),
path('editar/<uuid:empreendimento_uuid>/step4/', views_update.wizard_update_step4, name='empreendimento_update_step4'),
path('editar/<uuid:empreendimento_uuid>/step5/', views_update.wizard_update_step5, name='empreendimento_update_step5'),
path('editar/<uuid:empreendimento_uuid>/step6/', views_update.wizard_update_step6, name='empreendimento_update_step6'),

path('editar/<uuid:empreendimento_uuid>/representante/add/',
     views_update.wizard_update_rep_add, name='wizard_update_rep_add'),
path('editar/<uuid:empreendimento_uuid>/representante/<uuid:rep_uuid>/remover/',
     views_update.wizard_update_rep_del, name='wizard_update_rep_del'),
path('editar/<uuid:empreendimento_uuid>/representante/<uuid:rep_uuid>/doc/upload/',
     views_update.wizard_update_rep_doc_upload, name='wizard_update_rep_doc_upload'),
path('editar/<uuid:empreendimento_uuid>/representante/doc/<uuid:doc_uuid>/remover/',
     views_update.wizard_update_rep_doc_del, name='wizard_update_rep_doc_del'),

path('editar/<uuid:empreendimento_uuid>/doc/upload/',
     views_update.wizard_update_doc_upload, name='wizard_update_doc_upload'),
path('editar/<uuid:empreendimento_uuid>/doc/<uuid:doc_uuid>/remover/',
     views_update.wizard_update_doc_del, name='wizard_update_doc_del'),

path('editar/<uuid:empreendimento_uuid>/cancelar/',
     views_update.wizard_update_cancelar, name='wizard_update_cancelar'),
```

Atualizar botão "Editar" em `lista-empreendimentos-tabela.html`:
```html
<a href="{% url 'empreendimento_update_step1' empreendimento_uuid=empreendimento.uuid %}">Editar</a>
```
(Nome do kwarg tem que bater com o nome usado na `path()` —
`empreendimento_uuid`, igual ao padrão já usado em `alterar-empreendimento`.)

## `views_update.py`

Decorator em toda view/endpoint: `@has_permission_decorator('alterarEmpreendimento')`.

### `_get_or_create_draft(request, empreendimento_uuid)`

Busca `real = get_object_or_404(Empreendimento, uuid=empreendimento_uuid, is_ativo=True)`.
Sessão keyed por `str(empreendimento_uuid)`. Cria draft se ainda não
existir na sessão (ou se o uuid salvo não resolver mais — `DoesNotExist`
tratado criando um novo draft). Copia campos escalares + logo (via
`ContentFile`) + os 2 enderecos (`_copiar_endereco`, helper local, não em
services — é específico do mecanismo de draft, não uma operação de negócio
reaproveitável).

Retorna `(real, draft)`.

### `wizard_update_cancelar(request, empreendimento_uuid)`

`_deletar_draft` (helper local): se sessão tem draft pra esse uuid, deleta
enderecos do draft, deleta logo do draft (`arquivo.delete(save=False)`
equivalente pra ImageField), deleta draft, remove chave da sessão.
Redirect `lista-empreendimento-tabela`.

### Steps 1–3, 5

Mesmo padrão do cadastro, trocando `draft` de "só existe se sessão tiver"
pra "sempre existe via `_get_or_create_draft`", e trocando os redirects de
`empreendimento_wizard_stepN` pra `empreendimento_update_stepN` (com
`empreendimento_uuid=empreendimento_uuid` no redirect).

Step 2 e 3 reaproveitam `EmpresaStep2Form`/`EmpreendimentoStep3Form`/`EnderecoForm`
tal como estão (`instance=draft`, `instance=draft.endereco_empresa` etc — os
enderecos aqui são os do draft, não os do real).

Step 5: mesmo padrão direto-no-draft do cadastro (sem form dedicado).

### Step 4 — representantes

GET carrega representantes do **real**:
`RepresentanteLegal.objects.filter(empreendimento=real, is_ativo=True)`.

Reaproveita `RepresentanteFormSet` tal como o cadastro usa (um form por
representante existente + extras pra novos), com `queryset` filtrado no
**real** em vez do draft. POST do step (botão "Próximo") processa o
formset inteiro numa `transaction.atomic()`, igual ao
`wizard_step4` do cadastro: para cada form com `pk` existente chama
`services.atualizar_representante(rep, dados, endereco_dados)`; para form
novo sem `pk` chama `services.criar_representante(real, dados,
endereco_dados)`. Ou seja, edição de representante existente é escrita
direto no real — não fica em sessão, ao contrário do prompt original do
usuário (que pedia buffer de sessão pra esse caso). Decisão tomada na fase
de perguntas: manter tudo do step4 (add/remove/edit/doc) sempre imediato
no real, sem exceção — evita representante com "metade sessão, metade
real" dependendo de qual ação foi feita por último.

Os botões "Adicionar representante" e "Remover" continuam sendo os
endpoints AJAX imediatos abaixo (fora do submit do formset) — mesmo UX do
cadastro (adicionar já persiste o card com uuid real, permitindo upload de
documento na mesma tela sem esperar o "Próximo").

Endpoints AJAX (todos no real):
- `wizard_update_rep_add` — `services.criar_representante(real, dados, endereco_dados)`
- `wizard_update_rep_del` — `services.desativar_representante(rep)` (real
  está sempre ativo, então é sempre soft-delete — sem o `if draft.is_ativo`
  do cadastro)
- `wizard_update_rep_doc_upload` / `wizard_update_rep_doc_del` — idênticos
  aos do cadastro, trocando o objeto de referência pro real

### Step 6 — commit final

GET: lista `real.documentos.all()` + form de upload (igual step6 cadastro,
mas sem a seção "Modelos vinculados" reaproveitar modelo_vinculado do
draft — usa do real).

POST `finalizar`:
```python
with transaction.atomic():
    campos = ['nome', 'telefone', 'observacao', 'cnpj', 'razaoSocial',
              'codBanco', 'banco', 'agencia', 'conta', 'matricula',
              'cidade_foro', 'tempo_reserva', 'quantidade_parcela',
              'desconto', 'tipo_correcao']
    for campo in campos:
        setattr(real, campo, getattr(draft, campo))

    if draft.logo:
        if real.logo:
            real.logo.delete(save=False)
        real.logo.save(draft.logo.name.split('/')[-1], ContentFile(draft.logo.read()), save=False)

    real.endereco_empresa = empreendimento_services._copiar_endereco_draft_para_real(
        real.endereco_empresa, draft.endereco_empresa)
    real.endereco_empreendimento = empreendimento_services._copiar_endereco_draft_para_real(
        real.endereco_empreendimento, draft.endereco_empreendimento)

    real.full_clean(validate_unique=False)
    real.save()

_deletar_draft(request, empreendimento_uuid)  # fora do atomic
messages.success(request, 'Empreendimento atualizado com sucesso.')
return redirect('lista-empreendimento-tabela')
```

### Documentos do empreendimento (step 4 loop / step 6)

`wizard_update_doc_upload` / `wizard_update_doc_del` — idênticos ao
cadastro, operando em `real.documentos`.

**Obrigatório em toda remoção de documento** (representante e
empreendimento): `instance.arquivo.delete(save=False)` antes de
`instance.delete()` — sem isso o arquivo fica órfão no B2 (já é assim nas
funções existentes de `services.py`, só confirmando que o padrão se
mantém).

## Templates

Novo diretório `empreendimentos/templates/wizard/update/`:
```
_base_wizard_update.html
step1_dados_gerais.html
step2_empresa.html
step3_endereco.html
step4_representantes.html
step5_configuracoes.html
step6_documentos.html
```
Cópias dos templates de cadastro. Diferenças: título "Editar
Empreendimento"; steps bar e forms/AJAX apontam pras rotas de update (com
`empreendimento_uuid=empreendimento.uuid` — usar `real.uuid`, não
`draft.uuid`, em toda URL construída no template/JS); botão "Cancelar"
chama `wizard_update_cancelar`.

`empreendimento_wizard.js` é reaproveitado (mesma lógica de
`initRepresentantes`/`initDocumentosEmpreendimento`) — só as URLs passadas
pro JS mudam, já é o mecanismo `montarUrl()`/dummy-uuid existente.

## Smoke test

1. Abrir wizard update de empreendimento com dados/representantes/docs
   existentes — confirmar pré-preenchimento em cada step
2. Alterar nome (step1), CNPJ (step2), CEP (step3)
3. Step4: editar nome de representante existente, adicionar novo com
   endereço, remover o novo
4. Upload de documento no step4 (representante) e step6 (empreendimento)
5. Finalizar step6 — confirmar real atualizado, draft (+ enderecos + logo)
   deletados do banco
6. "Cancelar" no step3 — confirmar real intocado, draft deletado
7. Confirmar arquivos deletados (logo antigo do real no commit, docs
   removidos) não ficam órfãos no storage

## O que NÃO fazer

- Não alterar `views.py`, `forms.py`, `models.py`
- Não gerar migration
- Não alterar outro app
- Não remover campos legados `representante_nome/cpf/rg`
- Não implementar cleanup de draft órfão agora
