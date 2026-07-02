# Adicionar em documentos/views_documentos.py
# (ou manter separado em views_gerar.py e importar no urls.py)
#
# Fluxo:
#   1. Botão "Gerar Documento" na tela de venda → abre modal
#   2. Modal: escolhe tipo + modelo (padrão pré-selecionado) → POST para gerar_documento
#   3. gerar_documento chama services.gerar_documento_venda() → cria DocumentoGerado
#   4. Redireciona para documento_detalhe

from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from rolepermissions.decorators import has_permission_decorator
from rolepermissions.checkers import has_role
from core.roles import Administrador, Corretor

from vendas.models import RegisterVenda
from .models import (
    DocumentoGerado,
    ModeloDocumento,
    StatusDocumento,
    TipoDocumento,
)
from .services import gerar_documento_venda, finalizar_documento


# Tipos permitidos por role
_TIPOS_CORRETOR = {'proposta'}

# Tipos liberados enquanto o lote está em ANALISE — contrato só a partir de RESERVADO
_TIPOS_GATE_ANALISE = {'proposta'}


def _tipos_permitidos(user):
    """Retorna set de tipos que o usuário pode gerar/ver."""
    if has_role(user, Administrador):
        return {t.value for t in TipoDocumento}
    if has_role(user, Corretor):
        return _TIPOS_CORRETOR
    return set()


def _tipos_disponiveis(user, venda):
    """Tipos permitidos pro usuário, restritos por proposta aprovada com lastro.

    Contrato (e demais tipos além de proposta) só libera quando existe
    VendaDocumento vigente tipo=proposta_assinada, status=aprovado, com
    documento_gerado vinculado — prova que a aprovação corresponde a um
    DocumentoGerado real, não a um upload avulso. Critério NÃO depende mais
    de lote.situacao.
    """
    tipos_ok = _tipos_permitidos(user)
    proposta_com_lastro = bool(venda) and venda.documentos_assinados.vigentes().filter(
        tipo='proposta_assinada',
        status='aprovado',
        documento_gerado__isnull=False,
    ).exists()
    if not proposta_com_lastro:
        return tipos_ok & _TIPOS_GATE_ANALISE
    return tipos_ok


# ----------------------------------------------------------
# Gerar documento a partir de uma venda
# ----------------------------------------------------------
@has_permission_decorator('documentoGerar')
def gerar_documento(request, venda_pk):
    venda = get_object_or_404(
        RegisterVenda.objects.select_related('cliente', 'lote__quadra__empr'),
        pk=venda_pk,
    )
    empreendimento = venda.lote.quadra.empr
    tipos_ok = _tipos_disponiveis(request.user, venda)

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        modelo_id = request.POST.get('modelo_id') or None
        substitui_id = request.POST.get('substitui_id') or None

        if not tipo:
            messages.error(request, 'Selecione o tipo do documento.')
            return redirect(request.path)

        if tipo not in tipos_ok:
            messages.error(request, 'Você não tem permissão para gerar este tipo de documento.')
            return redirect(request.path)

        try:
            doc = gerar_documento_venda(
                venda=venda,
                tipo=tipo,
                usuario=request.user,
                modelo_id=int(modelo_id) if modelo_id else None,
                substitui_id=int(substitui_id) if substitui_id else None,
            )
            messages.success(request, f'Documento {doc.numero} gerado com sucesso.')
            return redirect('documentos:documento-detalhe', pk=doc.pk)
        except Exception as e:
            messages.error(request, str(e))
            return redirect(request.path)

    # GET — filtra modelos pelo que o usuário pode ver
    modelos_por_tipo = {}
    for tipo in TipoDocumento:
        if tipo.value not in tipos_ok:
            continue
        modelos = ModeloDocumento.objects.para_empreendimento(empreendimento, tipo=tipo.value)
        if modelos.exists():
            padrao = ModeloDocumento.objects.padrao_para(empreendimento, tipo.value)
            modelos_por_tipo[tipo.value] = {
                'label': tipo.label,
                'modelos': list(modelos.values('id', 'titulo', 'versao')),
                'padrao_id': padrao.pk if padrao else None,
            }

    # Documentos existentes filtrados pelo tipo permitido
    docs_existentes = DocumentoGerado.objects.filter(
        venda=venda,
        modelo__tipo__in=tipos_ok,
    ).exclude(status=StatusDocumento.CANCELADO).order_by('-criado_em')

    return render(request, 'documentos/gerar_documento_modal.html', {
        'venda': venda,
        'modelos_por_tipo': modelos_por_tipo,
        'docs_existentes': docs_existentes,
    })


# ----------------------------------------------------------
# Detalhe do documento gerado
# Corretor só acessa documentos de proposta
# ----------------------------------------------------------
@has_permission_decorator('documentoVisualizar')
def documento_detalhe(request, pk):
    doc = get_object_or_404(
        DocumentoGerado.objects.select_related(
            'modelo', 'venda__cliente', 'venda__lote__quadra__empr',
            'criado_por',
        ),
        pk=pk,
    )
    tipos_ok = _tipos_permitidos(request.user)
    if doc.modelo.tipo not in tipos_ok:
        messages.error(request, 'Você não tem permissão para visualizar este documento.')
        if doc.venda_id and doc.venda.lote_id:
            return redirect('analise', lote_uuid=doc.venda.lote.uuid)
        return HttpResponseForbidden('Acesso negado.')

    return render(request, 'documentos/documento_detalhe.html', {'doc': doc})


# ----------------------------------------------------------
# Finalizar documento — apenas Administrador
# ----------------------------------------------------------
@require_POST
@has_permission_decorator('documentoFinalizar')
def documento_finalizar(request, pk):
    if not has_role(request.user, Administrador):
        messages.error(request, 'Apenas administradores podem finalizar documentos.')
        return redirect('documentos:documento-detalhe', pk=pk)
    doc = get_object_or_404(DocumentoGerado, pk=pk)
    try:
        finalizar_documento(doc, request.user)
        messages.success(request, f'Documento {doc.numero} enviado para finalização.')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('documentos:documento-detalhe', pk=pk)


# ----------------------------------------------------------
# Status do documento (polling)
# ----------------------------------------------------------
def documento_status(request, pk):
    doc = get_object_or_404(DocumentoGerado.objects.only('status', 'arquivo_pdf'), pk=pk)
    return JsonResponse({
        'status': doc.status,
        'pdf_url': doc.arquivo_pdf.url if doc.arquivo_pdf else None,
    })


# ----------------------------------------------------------
# Cancelar documento — apenas Administrador
# ----------------------------------------------------------
@require_POST
@has_permission_decorator('documentoFinalizar')
def documento_cancelar(request, pk):
    if not has_role(request.user, Administrador):
        messages.error(request, 'Apenas administradores podem cancelar documentos.')
        return redirect('documentos:documento-detalhe', pk=pk)
    doc = get_object_or_404(DocumentoGerado, pk=pk)
    if doc.status == StatusDocumento.FINALIZADO:
        messages.error(request, 'Documento finalizado não pode ser cancelado.')
        return redirect('documentos:documento-detalhe', pk=pk)
    doc.status = StatusDocumento.CANCELADO
    doc.save(update_fields=['status'])
    messages.success(request, f'Documento {doc.numero} cancelado.')
    return redirect('documentos:documento-detalhe', pk=pk)


# ----------------------------------------------------------
# Preview do documento (iframe src)
# ----------------------------------------------------------
@xframe_options_sameorigin
@has_permission_decorator('documentoVisualizar')
def documento_preview(request, pk):
    from django.http import HttpResponse, HttpResponseForbidden
    doc = get_object_or_404(DocumentoGerado, pk=pk)
    tipos_ok = _tipos_permitidos(request.user)
    if doc.modelo.tipo not in tipos_ok:
        return HttpResponseForbidden('Sem permissão.')

    # CSS A4 injetado junto com o conteúdo
    css = '''
    <style>
      :root {
        --doc-font-family: 'Times New Roman', Times, serif;
        --doc-font-size: 12pt;
        --doc-line-height: 1.5;
        --doc-margin-top:    3cm;
        --doc-margin-right:  2cm;
        --doc-margin-bottom: 2cm;
        --doc-margin-left:   3cm;
        --doc-text-indent: 1.25cm;
      }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        background: #6c757d;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 32px 16px;
        min-height: 100vh;
        font-family: var(--doc-font-family);
        font-size: var(--doc-font-size);
        line-height: var(--doc-line-height);
        color: #000;
      }
      .a4-page {
        width: 210mm;
        min-height: 297mm;
        background: #fff;
        box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        padding: var(--doc-margin-top) var(--doc-margin-right) var(--doc-margin-bottom) var(--doc-margin-left);
        margin-bottom: 24px;
      }
      p {
        text-align: justify;
        text-indent: var(--doc-text-indent);
        margin-bottom: 0;
        line-height: var(--doc-line-height);
        font-size: var(--doc-font-size);
      }
      table p, td p, th p { text-indent: 0; margin: 0; }
      h1, h2, h3, h4, h5, h6 {
        font-family: var(--doc-font-family);
        font-size: var(--doc-font-size);
        font-weight: bold;
        text-align: center;
        margin: 6pt 0 4pt 0;
        text-indent: 0;
      }
      hr { border: none; border-top: 1px solid #000; margin: 8pt 0; }
      table {
        width: 100% !important;
        border-collapse: collapse;
        table-layout: fixed;
        word-wrap: break-word;
        font-size: var(--doc-font-size);
        line-height: var(--doc-line-height);
        margin-bottom: 4pt;
      }
      td, th {
        padding: 2pt 4pt;
        vertical-align: top;
        border: 1px solid #999;
        text-align: left;
        font-size: var(--doc-font-size);
      }
      col { min-width: 0 !important; width: auto !important; }
      @media print {
        @page { size: A4 portrait; margin: 0; }
        body { background: #fff !important; padding: 0 !important; display: block !important; }
        .a4-page {
          box-shadow: none !important;
          margin: 0 !important;
          width: 100% !important;
          min-height: auto !important;
          padding: var(--doc-margin-top) var(--doc-margin-right) var(--doc-margin-bottom) var(--doc-margin-left) !important;
        }
      }
    </style>
    '''

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  {css}
</head>
<body>
  <div class="a4-page">
    {doc.conteudo_final_html}
  </div>
</body>
</html>'''

    return HttpResponse(html)