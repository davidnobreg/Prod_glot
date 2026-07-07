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
from django.templatetags.static import static
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

# Tipos liberados quando não há proposta aprovada com lastro (ver _tipos_disponiveis)
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
def gerar_documento(request, venda_uuid):
    venda = get_object_or_404(
        RegisterVenda.objects.select_related('cliente', 'lote__quadra__empr'),
        uuid=venda_uuid,
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
            return redirect('documentos:documento-detalhe', documento_uuid=doc.uuid)
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

    return render(request, 'documentos/gerar_documento_standalone.html', {
        'venda': venda,
        'modelos_por_tipo': modelos_por_tipo,
        'docs_existentes': docs_existentes,
    })


# ----------------------------------------------------------
# Detalhe do documento gerado
# Corretor só acessa documentos de proposta
# ----------------------------------------------------------
@has_permission_decorator('documentoVisualizar')
def documento_detalhe(request, documento_uuid):
    doc = get_object_or_404(
        DocumentoGerado.objects.select_related(
            'modelo', 'venda__cliente', 'venda__lote__quadra__empr',
            'criado_por',
        ),
        uuid=documento_uuid,
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
def documento_finalizar(request, documento_uuid):
    if not has_role(request.user, Administrador):
        messages.error(request, 'Apenas administradores podem finalizar documentos.')
        return redirect('documentos:documento-detalhe', documento_uuid=documento_uuid)
    doc = get_object_or_404(DocumentoGerado, uuid=documento_uuid)
    try:
        finalizar_documento(doc, request.user)
        messages.success(request, f'Documento {doc.numero} enviado para finalização.')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('documentos:documento-detalhe', documento_uuid=documento_uuid)


# ----------------------------------------------------------
# Status do documento (polling)
# ----------------------------------------------------------
def documento_status(request, documento_uuid):
    doc = get_object_or_404(DocumentoGerado.objects.only('status', 'arquivo_pdf'), uuid=documento_uuid)
    return JsonResponse({
        'status': doc.status,
        'pdf_url': doc.arquivo_pdf.url if doc.arquivo_pdf else None,
    })


# ----------------------------------------------------------
# Cancelar documento — apenas Administrador
# ----------------------------------------------------------
@require_POST
@has_permission_decorator('documentoFinalizar')
def documento_cancelar(request, documento_uuid):
    if not has_role(request.user, Administrador):
        messages.error(request, 'Apenas administradores podem cancelar documentos.')
        return redirect('documentos:documento-detalhe', documento_uuid=documento_uuid)
    doc = get_object_or_404(DocumentoGerado, uuid=documento_uuid)
    if doc.status == StatusDocumento.FINALIZADO:
        messages.error(request, 'Documento finalizado não pode ser cancelado.')
        return redirect('documentos:documento-detalhe', documento_uuid=documento_uuid)
    doc.status = StatusDocumento.CANCELADO
    doc.save(update_fields=['status'])
    messages.success(request, f'Documento {doc.numero} cancelado.')
    return redirect('documentos:documento-detalhe', documento_uuid=documento_uuid)


# ----------------------------------------------------------
# Preview do documento (iframe src)
# ----------------------------------------------------------
@xframe_options_sameorigin
@has_permission_decorator('documentoVisualizar')
def documento_preview(request, documento_uuid):
    from django.http import HttpResponse, HttpResponseForbidden
    doc = get_object_or_404(DocumentoGerado, uuid=documento_uuid)
    tipos_ok = _tipos_permitidos(request.user)
    if doc.modelo.tipo not in tipos_ok:
        return HttpResponseForbidden('Sem permissão.')

    empreendimento = (
        doc.venda.lote.quadra.empr
        if doc.venda and doc.venda.lote else None
    )
    cfg = getattr(empreendimento, 'config_documento', None) if empreendimento else None

    margem_sup = cfg.margem_sup if cfg else 25
    margem_dir = cfg.margem_dir if cfg else 20
    margem_inf = cfg.margem_inf if cfg else 20
    margem_esq = cfg.margem_esq if cfg else 30
    fonte_familia = cfg.fonte_familia if cfg and cfg.fonte_familia else 'Times New Roman'
    fonte_tamanho = cfg.fonte_tamanho if cfg and cfg.fonte_tamanho else 12

    # Mesmas margens/fonte de documento_base.html (PDF real), pra que o
    # preview/impressão bata com o PDF gerado — só o letterbox cinza de tela
    # é exclusivo daqui, zerado no @media print.
    css = f'''
    <link rel="stylesheet" href="{static('documentos/css/documento_a4.css')}">
    <style>
      body {{
        background: #6c757d;
        padding: 32px 16px;
        min-height: 100vh;
      }}
      .a4-page {{
        width: 210mm;
        min-height: 297mm;
        margin: 0 auto 24px;
        background: #fff;
        box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        box-sizing: border-box;
        padding: {margem_sup}mm {margem_dir}mm {margem_inf}mm {margem_esq}mm;
        font-family: "{fonte_familia}", serif;
        font-size: {fonte_tamanho}pt;
      }}
      @media print {{
        @page {{ size: A4 portrait; margin: 0; }}
        body {{ background: #fff !important; padding: 0 !important; min-height: 0 !important; }}
        .a4-page {{
          box-shadow: none !important;
          margin: 0 !important;
          width: 100% !important;
          min-height: auto !important;
        }}
      }}
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
    <main class="documento-conteudo">
      {doc.conteudo_final_html}
    </main>
  </div>
</body>
</html>'''

    return HttpResponse(html)