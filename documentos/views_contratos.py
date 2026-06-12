# documentos/views_contratos.py
#
# Opção B — substitui as 4 views legadas pelo novo módulo ModeloDocumento.
# Cole este arquivo em documentos/ e importe no urls.py (ver script 3).

import hashlib

from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from weasyprint import HTML, CSS

from rolepermissions.decorators import has_permission_decorator

from vendas.models import RegisterVenda
from .models import ModeloDocumento, DocumentoGerado, StatusDocumento, SequencialDocumento
from .services import montar_contexto_venda, renderizar_variaveis


# ----------------------------------------------------------
# CSS compartilhado para geração de PDF
# ----------------------------------------------------------
_PDF_CSS = CSS(string='''
    @page {
        size: A4 portrait;
        margin: 20mm 20mm 20mm 30mm;
    }
    body {
        font-family: "Times New Roman", serif;
        font-size: 12pt;
        line-height: 1.5;
        color: #000;
    }
    nav, header, footer, .navbar, .btn, #btn-imprimir {
        display: none !important;
    }
    p { text-align: justify; margin: 0 0 6pt 0; }
    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 4pt; font-size: 11pt; }
    h1, h2, h3 { margin: 0 0 6pt 0; }
''')

_WATERMARK_CSS = CSS(string='''
    body::before {
        content: "RASCUNHO";
        position: fixed;
        top: 45%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-35deg);
        font-size: 90px;
        font-weight: bold;
        color: rgba(0, 0, 0, 0.10);
        z-index: 9999;
        pointer-events: none;
        white-space: nowrap;
    }
''')


def _get_venda(venda_uuid):
    return get_object_or_404(
        RegisterVenda.objects.select_related(
            'cliente',
            'lote__quadra__empr',
            'user',
        ),
        uuid=venda_uuid,
    )


def _modelo_ou_404(empreendimento, tipo):
    modelo = ModeloDocumento.objects.padrao_para(empreendimento, tipo)
    if not modelo:
        raise Http404(
            f"Nenhum modelo de '{tipo}' configurado para {empreendimento}. "
            f"Cadastre um modelo em Documentos → Modelos."
        )
    return modelo


def _html_renderizado(modelo, venda, usuario):
    contexto = montar_contexto_venda(venda, usuario)
    return renderizar_variaveis(modelo.conteudo_html, contexto)


def _pdf_response(html, nome_arquivo, stylesheets=None):
    sheets = stylesheets or [_PDF_CSS]
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
    HTML(string=html).write_pdf(response, stylesheets=sheets)
    return response


# ----------------------------------------------------------
# VIEW: contrato (HTML — substitui a view legada contrato())
# ----------------------------------------------------------
@has_permission_decorator('contrato')
def contrato(request, venda_uuid):
    """
    Renderiza contrato de venda via ModeloDocumento.
    Substitui a view legada que buscava via empr.contrato.id (FK CadastroDocumento).
    """
    venda = _get_venda(venda_uuid)
    empreendimento = venda.lote.quadra.empr
    modelo = _modelo_ou_404(empreendimento, 'contrato')
    html_final = _html_renderizado(modelo, venda, request.user)
    return render(request, 'documentos/preview_contrato.html', {
        'html_final': html_final,
        'venda': venda,
        'modelo': modelo,
    })


# ----------------------------------------------------------
# VIEW: contrato_pdf (PDF — substitui contrato_pdf1)
# ----------------------------------------------------------
@has_permission_decorator('contrato')
def contrato_pdf(request, venda_uuid):
    """
    Gera PDF do contrato via WeasyPrint.
    Substitui contrato_pdf1 (que tinha id=3 hardcoded e usava GET param).
    Agora recebe venda_uuid na URL, consistente com o restante do módulo.
    """
    venda = _get_venda(venda_uuid)
    empreendimento = venda.lote.quadra.empr
    modelo = _modelo_ou_404(empreendimento, 'contrato')
    html_final = _html_renderizado(modelo, venda, request.user)
    nome = f'contrato_{venda.cliente.name}_{venda_uuid}.pdf'
    return _pdf_response(html_final, nome)


# ----------------------------------------------------------
# VIEW: proposta_pdf (PDF — substitui proposta_pdf legado)
# ----------------------------------------------------------
@has_permission_decorator('proposta')
def proposta_pdf(request, venda_uuid):
    """
    Gera PDF da proposta via WeasyPrint.
    Substitui a versão legada que buscava tipo='contrato' (bug de tipo).
    """
    venda = _get_venda(venda_uuid)
    empreendimento = venda.lote.quadra.empr
    modelo = _modelo_ou_404(empreendimento, 'proposta')
    html_final = _html_renderizado(modelo, venda, request.user)
    nome = f'proposta_{venda.cliente.name}_{venda_uuid}.pdf'
    return _pdf_response(html_final, nome)


# ----------------------------------------------------------
# VIEW: proposta_rascunho (HTML com watermark — substitui propostaRascunho)
# ----------------------------------------------------------
@has_permission_decorator('propostaRascunho')
def proposta_rascunho(request, venda_uuid):
    """
    Proposta com marca d'água RASCUNHO.
    Substitui propostaRascunho que buscava lote__uuid e usava CadastroDocumento.
    Agora usa venda__uuid (consistente) + ModeloDocumento.
    """
    venda = get_object_or_404(
        RegisterVenda.objects.select_related('cliente', 'lote__quadra__empr'),
        uuid=venda_uuid,
    )
    empreendimento = venda.lote.quadra.empr
    modelo = _modelo_ou_404(empreendimento, 'proposta')
    html_final = _html_renderizado(modelo, venda, request.user)
    return render(request, 'documentos/preview_rascunho.html', {
        'html_final': html_final,
        'venda': venda,
        'is_rascunho': True,
    })


# ----------------------------------------------------------
# VIEW: proposta_rascunho_pdf (PDF com watermark — bônus)
# ----------------------------------------------------------
@has_permission_decorator('propostaRascunho')
def proposta_rascunho_pdf(request, venda_uuid):
    """PDF do rascunho com watermark via WeasyPrint."""
    venda = get_object_or_404(
        RegisterVenda.objects.select_related('cliente', 'lote__quadra__empr'),
        uuid=venda_uuid,
    )
    empreendimento = venda.lote.quadra.empr
    modelo = _modelo_ou_404(empreendimento, 'proposta')
    html_final = _html_renderizado(modelo, venda, request.user)
    nome = f'rascunho_{venda.cliente.name}_{venda_uuid}.pdf'
    return _pdf_response(html_final, nome, stylesheets=[_PDF_CSS, _WATERMARK_CSS])
