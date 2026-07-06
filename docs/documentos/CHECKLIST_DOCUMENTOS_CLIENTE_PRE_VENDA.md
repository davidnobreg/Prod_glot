# Checklist de Documentos do Cliente — Pré-Venda

Regra que define quais documentos um cliente (PF ou PJ) precisa ter cadastrados para liberar a
transição de uma venda entre os status `RESERVADO → PRE-VENDA` e `PRE-VENDA → VENDIDO`. É bloqueio
real no backend, não só indicador visual.

## Como PF/PJ é decidido

Não existe campo `tipo_pessoa` no model `Cliente`. É inferido pelo tamanho do campo `documento`
(só dígitos):

- 11 dígitos → Pessoa Física (PF)
- 14 dígitos → Pessoa Jurídica (PJ)

Fonte: `vendas/services.py:15`.

## Documentos obrigatórios

### Pessoa Física (PF)

| Documento | Condição de exigência |
|---|---|
| `CNH` | Exigido se o cliente **não** tiver CNH cadastrada |
| `RG` + `CPF` | Exigidos **somente se** o cliente não tiver `CNH` cadastrada (CNH substitui RG+CPF) |
| `COMPROVANTE_RESIDENCIA` | Sempre |
| `COMPROVANTE_ESTADO_CIVIL` | Exigido quando `Cliente.estado_civil` for diferente de `solteiro`/`solteira` (casado, divorciado, viúvo, separado judicialmente, união estável, etc. — todos exigem) |

### Pessoa Jurídica (PJ)

| Documento | Condição de exigência |
|---|---|
| `CNPJ` | Sempre |
| `CONTRATO_SOCIAL` | Sempre |
| `RG_CPF_ADMINISTRADOR` | Sempre |
| `COMPROVANTE_RESIDENCIA` | Sempre |

Não há condicionais para PJ — a lista é fixa.

## Critério de "documento disponível"

Existe um `ClienteDocumento` (`clientes/models.py:121-179`) daquele `tipo` com `status='disponivel'`.
Documentos com `status='processando'` ou `status='erro'` contam como **pendentes** (não liberam a
pré-venda).

## Requisito adicional (fora do checklist de documentos do cliente)

Além do checklist acima, as mesmas views exigem que a **proposta** e o **contrato** estejam
assinados, aprovados e vinculados a um `DocumentoGerado` (lastro documental):

- `vendas/views/create_views.py:24-27, 43-55, 85-105`

Essa condição é separada e independente do checklist de documentos do cliente — as duas precisam
estar satisfeitas para liberar a venda.

## Onde a regra é aplicada

**Fonte única de verdade (não duplicar):** `checklist_documentos_cliente(cliente)` em
`vendas/services.py:7-42`.

**Gates reais (bloqueio server-side):**

| Transição | View | Local |
|---|---|---|
| `RESERVADO → PRE-VENDA` | `CriarVendaView.post` | `vendas/views/create_views.py:107-113` |
| `PRE-VENDA → VENDIDO` | `EfetivarVendaView.post` | `vendas/views/create_views.py:57-63` |

**Exibição na UI (mesmo `context['checklist_cliente']`, calculado pela mesma função):**

- `vendas/templates/vendas/pre_venda_detalhe.html:366-383` (tela Pré-Venda)
- `vendas/templates/reservado_detalhe.html:489-513` (tela Reserva/Detalhes)

## Débito técnico conhecido (fora de escopo)

- A lógica "PF se `documento` tem 11 dígitos, senão PJ" está duplicada em 3 lugares:
  `clientes/forms.py:135`, `clientes/views.py:94-97`, `vendas/services.py:15`. Oportunidade futura:
  extrair para uma função única (ex: `Cliente.tipo_pessoa` como property).
- O markup do checklist está duplicado em 2 templates (`pre_venda_detalhe.html` e
  `reservado_detalhe.html`), sem partial compartilhado. Oportunidade futura: extrair para um
  `{% include %}` único.
