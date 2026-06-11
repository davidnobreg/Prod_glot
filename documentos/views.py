import locale
import os
import re
from django.conf import settings
from django.template import Template, Context
from django.utils.timezone import now

from django.utils import timezone
from babel.dates import format_date

from reportlab.platypus import Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import cm
from num2words import num2words

from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

from .models import CadastroDocumento, ModeloDocumento
from .services import (
    construir_contexto_venda,
    montar_contexto_venda,
    renderizar_variaveis,
)
from clientes.models import ClienteTelefone
from vendas.models import RegisterVenda
from weasyprint import HTML, CSS
from django.utils.decorators import method_decorator
from rolepermissions.decorators import has_permission_decorator


def draw_header_footer(canvas, doc):
    canvas.saveState()

    """# 🔹 LOGO (opcional)
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')
    if os.path.exists(logo_path):
        canvas.drawImage(
            logo_path,
            2 * cm,
            27 * cm,
            width=3 * cm,
            preserveAspectRatio=True,
            mask='auto'
        )"""

    # 🔹 TÍTULO
    canvas.setFont('Helvetica-Bold', 12)
    canvas.drawString(
        6 * cm,
        28 * cm,
        "CONTRATO DE COMPRA E VENDA"
    )

    # 🔹 DATA
    canvas.setFont('Helvetica', 9)
    canvas.drawString(
        6 * cm,
        27.4 * cm,
        f"Emitido em: {doc.issue_date}"
    )

    # 🔹 RODAPÉ — PÁGINA
    """canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(
        A4[0] / 2,
        1.5 * cm,
        f"Página {doc.page}"
    )

    canvas.restoreState()"""


def bloco_assinaturas():
    tabela = Table(
        [
            ["", "", ""],
            ["______________________________", "", "______________________________"],
            ["Comprador", "", "Empresa"],
            ["", "", ""],
            ["______________________________", "", "______________________________"],
            ["Testemunha 1", "", "Testemunha 2"],
        ],
        colWidths=[7 * cm, 1 * cm, 7 * cm]
    )

    tabela.setStyle(TableStyle([
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LINEBELOW', (0, 1), (0, 1), 1, colors.black),
        ('LINEBELOW', (2, 1), (2, 1), 1, colors.black),
        ('LINEBELOW', (0, 4), (0, 4), 1, colors.black),
        ('LINEBELOW', (2, 4), (2, 4), 1, colors.black),
    ]))

    return tabela


# =====================================================
# HELPERS
# =====================================================

def _get_venda(venda_uuid, por_lote=False):
    qs = RegisterVenda.objects.select_related(
        'cliente',
        'lote',
        'lote__quadra',
        'lote__quadra__empr',
        'user',
    )
    campo = 'lote__uuid' if por_lote else 'uuid'
    return get_object_or_404(qs, **{campo: venda_uuid})


def _renderizar_documento(tipo, contexto):
    documento = (
        CadastroDocumento.objects
        .filter(tipo=tipo, ativo=True)
        .order_by('-versao')
        .first()
    )
    if not documento:
        raise Http404(f"Documento '{tipo}' não encontrado")
    return Template(documento.texto).render(Context(contexto))


def _injetar_watermark(html_final, texto="EM ANALISES"):
    watermark_css = f"""
<style>
    #conteudo::before {{
        content: "{texto}";
        position: fixed;
        top: 45%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-35deg);
        font-size: 90px;
        font-weight: bold;
        color: rgba(0, 0, 0, 0.12);
        z-index: 9999;
        pointer-events: none;
        white-space: nowrap;
    }}
</style>
"""
    if '</head>' in html_final:
        return html_final.replace('</head>', f'{watermark_css}</head>', 1)
    return f'{watermark_css}{html_final}'


def _limpar_html_pdf(html_final):
    for texto_rodape in [
        '© 2025 David Nóbrega - Todos os direitos reservados',
        '© 2025 David Nóbrega - Todos os direitos reservadose',
        'Â© 2025 David NÃ³brega - Todos os direitos reservados',
        'Â© 2025 David NÃ³brega - Todos os direitos reservadose',
    ]:
        html_final = html_final.replace(texto_rodape, '')

    html_final = re.sub(r'<nav[\s\S]*?</nav>', '', html_final, flags=re.IGNORECASE)
    html_final = re.sub(r'<footer[\s\S]*?</footer>', '', html_final, flags=re.IGNORECASE)
    html_final = re.sub(r'<header[\s\S]*?</header>', '', html_final, flags=re.IGNORECASE)
    return html_final


_PDF_CSS = '''

    @page {
        size: A4 portrait;
        margin: 2mm;
    }

    html,
    body{
        margin:0;
        padding:0;
        width:100%;
    }

    body{
        font-family: Arial, sans-serif;
        font-size: 7px;
        line-height: 1;
        color:#000;
    }

    nav,
    header,
    footer,
    .navbar,
    .btn,
    .btn-voltar,
    #btn-imprimir{
        display:none !important;
    }

    .container,
    .container-fluid,
    .table-responsive,
    .row,
    [class*="col-"]{
        width:100% !important;
        max-width:100% !important;
        margin:0 !important;
        padding:0 !important;
    }

    .my-5,
    .mt-5,
    .mt-4,
    .mb-4,
    .p-3{
        margin:0 !important;
        padding:0 !important;
    }

    p{
        margin:0;
        text-align:justify;
    }

    table{
        width:100%;
        border-collapse:collapse;
    }

    td,
    th{
        padding:1px;
        font-size:7px;
        line-height:1;
    }

    h1,
    h2,
    h3,
    h4,
    h5,
    h6{
        margin:0 0 2px 0;
        padding:0;
    }

    h3{
        font-size:9px;
    }

    hr{
        margin:1px 0;
    }

    img{
        max-height:35px !important;
        width:auto !important;
    }

    .border{
        border:0 !important;
    }

    .titulo{
        text-align:center;
        font-size:9px;
        font-weight:bold;
        margin-bottom:2px;
    }

    .evitar-quebra{
        page-break-inside: avoid;
    }

    .quebra{
        page-break-before: always;
    }

    br{
        display:none;
    }

    .data-local-print,
    .assinaturas-print{
        margin-top:3mm !important;
    }

    .assinaturas{
        font-size:7px;
        line-height:1;
    }

'''


def _gerar_pdf(html_final, nome_arquivo):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    HTML(string=html_final).write_pdf(response, stylesheets=[CSS(string=_PDF_CSS)])
    return response


# =====================================================
# VIEWS
# =====================================================

@has_permission_decorator('proposta')
def proposta(request, venda_uuid):
    """Proposta via novo módulo de documentos (ModeloDocumento + variáveis globais).

    Busca o modelo de proposta padrão do empreendimento (ou o global como
    fallback), renderiza com o contexto da venda e exibe na tela de preview
    existente. Sem modelo no novo módulo, cai na view legada.
    """
    venda = _get_venda(venda_uuid)
    empreendimento = venda.lote.quadra.empr
    modelo = ModeloDocumento.objects.padrao_para(empreendimento, 'proposta')
    if not modelo:
        return proposta_legado(request, venda_uuid)
    contexto = montar_contexto_venda(venda, request.user)
    html_final = renderizar_variaveis(modelo.conteudo_html, contexto)
    return render(request, 'proposta.html', {
        'html_final': html_final,
        'venda': venda,
    })


@has_permission_decorator('proposta')
def proposta_legado(request, venda_uuid):
    venda = _get_venda(venda_uuid)
    contato_cliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()
    contexto = construir_contexto_venda(venda, contato_cliente)
    html_final = _renderizar_documento('proposta', contexto)
    return render(request, 'proposta.html', {
        'html_final': html_final,
        'venda': venda,
    })


@has_permission_decorator('propostaRascunho')
def propostaRascunho(request, venda_uuid):
    venda = _get_venda(venda_uuid, por_lote=True)
    contato_cliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()
    contexto = construir_contexto_venda(venda, contato_cliente)
    html_final = _injetar_watermark(_renderizar_documento('proposta', contexto))
    return render(request, 'proposta.html', {
        'html_final': html_final,
        'venda': venda,
        'is_rascunho': True,
    })


def proposta_pdf(request, venda_uuid):
    venda = _get_venda(venda_uuid)
    contato_cliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()
    contexto = construir_contexto_venda(venda, contato_cliente)
    html_final = _limpar_html_pdf(_renderizar_documento('contrato', contexto))
    return _gerar_pdf(html_final, f'proposta_{venda.cliente.name}.pdf')


def preparar_contrato(request):
    # 1. Buscar contrato ativo
    contrato = get_object_or_404(Contrato, ativo=True)

    # 2. Dados que virão do sistema (exemplo)
    dados = {
        'vendedor': 'Empresa XYZ LTDA',
        'comprador': 'João da Silva',
        'lote': '12',
        'empreendimento': 'Residencial Sol Nascente',
        'valor': '120.000,00',
        'cidade': 'Fortaleza',
        'data': now().strftime('%d/%m/%Y'),
    }

    # 3. Substituir variáveis do contrato
    texto_processado = contrato.conteudo
    for chave, valor in dados.items():
        texto_processado = texto_processado.replace(
            f'{{{{ {chave} }}}}', str(valor)
        )

    # 4. Retornar para teste (debug)
    return HttpResponse(texto_processado)


def contrato(request, venda_uuid):
    venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
    contatoCliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()

    documento = get_object_or_404(
        CadastroDocumento,
        # tipo = 'venda',
        id=venda.lote.quadra.empr.contrato.id,  # 🔥 aqui está a mágica
        ativo=True
    )

    template = Template(documento.texto)

    html_final = template.render(Context({
        'empreendimento': venda,
        'comprador': venda.cliente,
        'enderecoCliente': venda.cliente,
        'contatoCliente': contatoCliente,
        'conjuge': venda.cliente,
        # 'cpf': venda.cliente.cpf,
        # 'lote': venda.lote.numero,
        # 'quadra': venda.lote.quadra.nome,
        # 'valor': venda.valor_total,
        # 'data': venda.data_venda.strftime('%d/%m/%Y'),
    }))

    return HttpResponse(html_final)


def contrato_pdf1(request):
    venda = get_object_or_404(RegisterVenda, id=request.GET.get('venda_id'))
    contatoCliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()

    documento = get_object_or_404(
        CadastroDocumento,
        # tipo = 'venda'
        id=3,  # venda.lote.quadra.empr.contrato.id,  # 🔥 aqui está a mágica
        ativo=True
    )

    template = Template(documento.texto)

    html_final = template.render(Context({
        'empreendimento': venda,
        'comprador': venda.cliente,
        'enderecoCliente': venda.cliente,
        'contatoCliente': contatoCliente,
        'conjuge': venda.cliente,
        # 'cpf': venda.cliente.cpf,
        # 'lote': venda.lote.numero,
        # 'quadra': venda.lote.quadra.nome,
        # 'valor': venda.valor_total,
        # 'data': venda.data_venda.strftime('%d/%m/%Y'),
    }))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="documento.pdf"'

    HTML(string=html_final).write_pdf(response)
    return response
