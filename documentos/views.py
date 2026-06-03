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

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

from .models import CadastroDocumento
from clientes.models import ClienteEndereco, ClienteTelefone, ClienteConjuge
from vendas.models import RegisterVenda
from weasyprint import HTML, CSS


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


def proposta(request, venda_uuid):
    venda = get_object_or_404(
        RegisterVenda.objects.select_related(
            'cliente',
            'lote',
            'lote__quadra',
            'lote__quadra__empr',
            'user',
        ),
        uuid=venda_uuid
    )

    endereco_cliente = ClienteEndereco.objects.filter(
        cliente=venda.cliente
    ).first()

    contato_cliente = ClienteTelefone.objects.filter(
        cliente=venda.cliente
    ).first()

    conjuge = ClienteConjuge.objects.filter(
        cliente=venda.cliente
    ).first()

    data_atual = timezone.now().date()

    data_por_extenso = format_date(
        data_atual,
        format="d 'de' MMMM 'de' y",
        locale='pt_BR'
    )

    get_tempo = venda.lote.quadra.empr

    # ======================
    # HELPERS
    # ======================
    def formatar_moeda_br(valor):

        return (
            f"R$ {float(valor):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # ======================
    # VALOR TOTAL
    # ======================
    try:

        area = float(
            venda.lote.area or 0
        )

        valor_metro = float(
            venda.lote.valor_metro_quadrado or 0
        )

        valor = (
                area * valor_metro
        )

    except (
            TypeError,
            ValueError
    ):

        valor = 0

    # ======================
    # PARCELAS
    # ======================
    try:

        total_parcelas = int(
            venda.quantidade_parcelas or 0
        )

    except (
            TypeError,
            ValueError,
            AttributeError
    ):

        total_parcelas = 0

    # ======================
    # CORREÇÃO
    # ======================
    try:

        correcao = float(
            get_tempo.correcao or 0
        )

    except (
            TypeError,
            ValueError,
            AttributeError
    ):

        correcao = 0

    valor_corrigido = valor + (
            valor * (correcao / 100)
    )

    # ======================
    # SINAL
    # ======================
    try:

        sinal = float(
            venda.valor_sinal or 0
        )

    except (
            TypeError,
            ValueError
    ):

        sinal = 0

    # ======================
    # SINAL EXTENSO
    # ======================
    try:

        valor_extenso = num2words(
            sinal,
            lang='pt_BR',
            to='currency'
        ).upper()

    except (
            TypeError,
            ValueError
    ):

        valor_extenso = 0

    # ======================
    # ENTRADA
    # ======================
    try:

        entrada = float(
            venda.valor_entrada or 0
        )

    except (
            TypeError,
            ValueError
    ):

        entrada = 0

    # ======================
    # DESCONTO
    # ======================
    try:

        valor_desconto = float(
            venda.valor_desconto or 0
        )

    except (
            TypeError,
            ValueError
    ):

        valor_desconto = 0

    # ======================
    # VALOR FINANCIADO
    # ======================
    valor_financiado = (
            valor_corrigido
            - entrada
            - valor_desconto
    )

    # ======================
    # VALOR PARCELA
    # ======================
    try:

        valor_parcela = float(
            venda.valor_parcela or 0
        )

    except (
            TypeError,
            ValueError
    ):

        valor_parcela = 0

    # ======================
    # REAJUSTE
    # ======================
    if venda.reajuste:

        tipo_reajuste = (
            venda.lote.quadra.empr.tipo_correcao
            if venda.lote.quadra.empr.tipo_correcao
            else "IGPM"
        )

        frase_reajuste = (
            f"AS PARCELAS SERÃO CORRIGIDAS PELO {tipo_reajuste}."
        )

    else:

        frase_reajuste = (
            "AS PARCELAS SERÃO FIXAS."
        )

    # ======================
    # FORMATADOS
    # ======================
    valor_total_formatado = (
        formatar_moeda_br(valor)
    )

    valor_entrada_formatado = (
        formatar_moeda_br(entrada)
    )

    valor_sinal_formatado = (
        formatar_moeda_br(sinal)
    )

    valor_desconto_formatado = (
        formatar_moeda_br(valor_desconto)
    )

    valor_parcela_formatado = (
        formatar_moeda_br(valor_parcela)
    )

    valor_financiado_formatado = (
        formatar_moeda_br(valor_financiado)
    )

    valor_corrigido_formatado = (
        formatar_moeda_br(valor_corrigido)
    )

    data_primeira_parcela = (
        venda.dt_primeira_parcela
    )

    documento = get_object_or_404(
        CadastroDocumento,
        id=1,
        ativo=True
    )

    template = Template(
        documento.texto
    )

    html_final = template.render(Context({

        'venda':
            venda,

        'endereco_cliente':
            endereco_cliente,

        'contato_cliente':
            contato_cliente,

        'conjuge':
            conjuge,

        'data_por_extenso':
            data_por_extenso,

        'valor_entrada_formatado':
            valor_entrada_formatado,

        'valor_sinal_formatado':
            valor_sinal_formatado,

        'valor_extenso':
            valor_extenso,

        'valor_desconto_formatado':
            valor_desconto_formatado,

        'valor_total_formatado':
            valor_total_formatado,

        'valor_parcela_formatado':
            valor_parcela_formatado,

        'valor_financiado_formatado':
            valor_financiado_formatado,

        'valor_corrigido_formatado':
            valor_corrigido_formatado,

        'data_primeira_parcela':
            data_primeira_parcela,

        'total_parcelas':
            total_parcelas,

        'correcao':
            correcao,

        'frase_reajuste':
            frase_reajuste,

        'observacao':
            venda.observacao,

    }))

    return HttpResponse(
        html_final
    )


def propostaRascunho(request, venda_uuid):
    venda = get_object_or_404(
        RegisterVenda.objects.select_related(
            'cliente',
            'lote',
            'lote__quadra',
            'lote__quadra__empr',
            'user',
        ),
        lote__uuid=venda_uuid
    )

    endereco_cliente = ClienteEndereco.objects.filter(
        cliente=venda.cliente
    ).first()

    contato_cliente = ClienteTelefone.objects.filter(
        cliente=venda.cliente
    ).first()

    conjuge = ClienteConjuge.objects.filter(
        cliente=venda.cliente
    ).first()

    data_atual = timezone.now().date()

    data_por_extenso = format_date(
        data_atual,
        format="d 'de' MMMM 'de' y",
        locale='pt_BR'
    )

    get_tempo = venda.lote.quadra.empr

    # ======================
    # HELPERS
    # ======================
    def formatar_moeda_br(valor):

        return (
            f"R$ {float(valor):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # ======================
    # VALOR TOTAL
    # ======================
    try:

        area = float(
            venda.lote.area or 0
        )

        valor_metro = float(
            venda.lote.valor_metro_quadrado or 0
        )

        valor = (
                area * valor_metro
        )

    except (
            TypeError,
            ValueError
    ):

        valor = 0

    # ======================
    # PARCELAS
    # ======================
    try:

        total_parcelas = int(
            venda.quantidade_parcelas or 0
        )

    except (
            TypeError,
            ValueError,
            AttributeError
    ):

        total_parcelas = 0

    # ======================
    # CORREÇÃO
    # ======================
    try:

        correcao = float(
            get_tempo.correcao or 0
        )

    except (
            TypeError,
            ValueError,
            AttributeError
    ):

        correcao = 0

    valor_corrigido = valor + (
            valor * (correcao / 100)
    )

    # ======================
    # SINAL
    # ======================
    try:

        sinal = float(
            venda.valor_sinal or 0
        )

    except (
            TypeError,
            ValueError
    ):

        sinal = 0

    # ======================
    # SINAL EXTENSO
    # ======================
    try:

        valor_extenso = num2words(
            sinal,
            lang='pt_BR',
            to='currency'
        ).upper()

    except (
            TypeError,
            ValueError
    ):

        valor_extenso = 0

    # ======================
    # ENTRADA
    # ======================
    try:

        entrada = float(
            venda.valor_entrada or 0
        )

    except (
            TypeError,
            ValueError
    ):

        entrada = 0

    # ======================
    # DESCONTO
    # ======================
    try:

        valor_desconto = float(
            venda.valor_desconto or 0
        )

    except (
            TypeError,
            ValueError
    ):

        valor_desconto = 0

    # ======================
    # VALOR FINANCIADO
    # ======================
    valor_financiado = (
            valor_corrigido
            - entrada
            - valor_desconto
    )

    # ======================
    # VALOR PARCELA
    # ======================
    try:

        valor_parcela = float(
            venda.valor_parcela or 0
        )

    except (
            TypeError,
            ValueError
    ):

        valor_parcela = 0

    # ======================
    # REAJUSTE
    # ======================
    if venda.reajuste:

        tipo_reajuste = (
            venda.lote.quadra.empr.tipo_correcao
            if venda.lote.quadra.empr.tipo_correcao
            else "IGPM"
        )

        frase_reajuste = (
            f"AS PARCELAS SERÃO CORRIGIDAS PELO {tipo_reajuste}."
        )

    else:

        frase_reajuste = (
            "AS PARCELAS SERÃO FIXAS."
        )

    # ======================
    # FORMATADOS
    # ======================
    valor_total_formatado = (
        formatar_moeda_br(valor)
    )

    valor_entrada_formatado = (
        formatar_moeda_br(entrada)
    )

    valor_sinal_formatado = (
        formatar_moeda_br(sinal)
    )

    valor_desconto_formatado = (
        formatar_moeda_br(valor_desconto)
    )

    valor_parcela_formatado = (
        formatar_moeda_br(valor_parcela)
    )

    valor_financiado_formatado = (
        formatar_moeda_br(valor_financiado)
    )

    valor_corrigido_formatado = (
        formatar_moeda_br(valor_corrigido)
    )

    data_primeira_parcela = (
        venda.dt_primeira_parcela
    )

    documento = get_object_or_404(
        CadastroDocumento,
        id=1,
        ativo=True
    )

    template = Template(
        documento.texto
    )

    html_final = template.render(Context({

        'venda':
            venda,

        'endereco_cliente':
            endereco_cliente,

        'contato_cliente':
            contato_cliente,

        'conjuge':
            conjuge,

        'data_por_extenso':
            data_por_extenso,

        'valor_entrada_formatado':
            valor_entrada_formatado,

        'valor_sinal_formatado':
            valor_sinal_formatado,

        'valor_extenso':
            valor_extenso,

        'valor_desconto_formatado':
            valor_desconto_formatado,

        'valor_total_formatado':
            valor_total_formatado,

        'valor_parcela_formatado':
            valor_parcela_formatado,

        'valor_financiado_formatado':
            valor_financiado_formatado,

        'valor_corrigido_formatado':
            valor_corrigido_formatado,

        'data_primeira_parcela':
            data_primeira_parcela,

        'total_parcelas':
            total_parcelas,

        'correcao':
            correcao,

        'frase_reajuste':
            frase_reajuste,

        'observacao':
            venda.observacao,

    }))

    watermark_css = """
<style>
    @media print {
        #conteudo::before {
            content: "RASCUNHO";
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
        }
    }
</style>
"""

    if '</head>' in html_final:
        html_final = html_final.replace(
            '</head>',
            f'{watermark_css}</head>',
            1
        )
    else:
        html_final = f'{watermark_css}{html_final}'

    return HttpResponse(
        html_final
    )

def proposta_pdf(request, venda_uuid):
    # =====================================================
    # VENDA
    # =====================================================

    venda = get_object_or_404(
        RegisterVenda.objects.select_related(
            'cliente',
            'lote',
            'lote__quadra',
            'lote__quadra__empr',
            'user',
        ),
        uuid=venda_uuid
    )

    endereco_cliente = ClienteEndereco.objects.filter(
        cliente=venda.cliente
    ).first()

    contato_cliente = ClienteTelefone.objects.filter(
        cliente=venda.cliente
    ).first()

    conjuge = ClienteConjuge.objects.filter(
        cliente=venda.cliente
    ).first()

    # =====================================================
    # DATA
    # =====================================================

    data_atual = timezone.now().date()

    data_por_extenso = format_date(
        data_atual,
        format="d 'de' MMMM 'de' y",
        locale='pt_BR'
    )

    empreendimento = venda.lote.quadra.empr

    # =====================================================
    # HELPERS
    # =====================================================

    def formatar_moeda_br(valor):

        try:

            return (
                f"R$ {float(valor):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        except (
                TypeError,
                ValueError
        ):

            return "R$ 0,00"

    # =====================================================
    # VALOR TOTAL
    # =====================================================

    try:

        area = float(
            venda.lote.area or 0
        )

        valor_metro = float(
            venda.lote.valor_metro_quadrado or 0
        )

        valor_total = (
                area * valor_metro
        )

    except (
            TypeError,
            ValueError
    ):

        valor_total = 0

    # =====================================================
    # PARCELAS
    # =====================================================

    try:

        total_parcelas = int(
            venda.quantidade_parcelas or 0
        )

    except (
            TypeError,
            ValueError,
            AttributeError
    ):

        total_parcelas = 0

    # =====================================================
    # CORREÇÃO
    # =====================================================

    try:

        correcao = float(
            empreendimento.correcao or 0
        )

    except (
            TypeError,
            ValueError,
            AttributeError
    ):

        correcao = 0

    valor_corrigido = (
            valor_total +
            (
                    valor_total *
                    (correcao / 100)
            )
    )

    # =====================================================
    # SINAL
    # =====================================================

    try:

        sinal = float(
            venda.valor_sinal or 0
        )

    except (
            TypeError,
            ValueError
    ):

        sinal = 0

    # =====================================================
    # ENTRADA
    # =====================================================

    try:

        entrada = float(
            venda.valor_entrada or 0
        )

    except (
            TypeError,
            ValueError
    ):

        entrada = 0

    # =====================================================
    # DESCONTO
    # =====================================================

    try:

        valor_desconto = float(
            venda.valor_desconto or 0
        )

    except (
            TypeError,
            ValueError
    ):

        valor_desconto = 0

    # =====================================================
    # VALOR FINANCIADO
    # =====================================================

    valor_financiado = (
            valor_corrigido
            - entrada
            - valor_desconto
    )

    # =====================================================
    # VALOR PARCELA
    # =====================================================

    try:

        valor_parcela = float(
            venda.valor_parcela or 0
        )

    except (
            TypeError,
            ValueError
    ):

        valor_parcela = 0

    # =====================================================
    # VALOR EXTENSO
    # =====================================================

    try:

        valor_extenso = num2words(
            sinal,
            lang='pt_BR',
            to='currency'
        ).upper()

    except (
            TypeError,
            ValueError
    ):

        valor_extenso = ''

    # =====================================================
    # REAJUSTE
    # =====================================================

    if venda.reajuste:

        tipo_reajuste = (
            empreendimento.tipo_correcao
            if empreendimento.tipo_correcao
            else 'IGPM'
        )

        frase_reajuste = (
            f'AS PARCELAS SERÃO CORRIGIDAS '
            f'PELO {tipo_reajuste}.'
        )

    else:

        frase_reajuste = (
            'AS PARCELAS SERÃO FIXAS.'
        )

    # =====================================================
    # FORMATADOS
    # =====================================================

    valor_total_formatado = (
        formatar_moeda_br(valor_total)
    )

    valor_entrada_formatado = (
        formatar_moeda_br(entrada)
    )

    valor_sinal_formatado = (
        formatar_moeda_br(sinal)
    )

    valor_desconto_formatado = (
        formatar_moeda_br(valor_desconto)
    )

    valor_parcela_formatado = (
        formatar_moeda_br(valor_parcela)
    )

    valor_financiado_formatado = (
        formatar_moeda_br(valor_financiado)
    )

    valor_corrigido_formatado = (
        formatar_moeda_br(valor_corrigido)
    )

    # =====================================================
    # DOCUMENTO HTML
    # =====================================================

    documento = get_object_or_404(
        CadastroDocumento,
        id=2,
        ativo=True
    )

    template = Template(
        documento.texto
    )

    contexto = {

        # =================================================
        # OBJETOS
        # =================================================

        'venda':
            venda,

        'endereco_cliente':
            endereco_cliente,

        'contato_cliente':
            contato_cliente,

        'conjuge':
            conjuge,

        # =================================================
        # DATAS
        # =================================================

        'data_por_extenso':
            data_por_extenso,

        'data_primeira_parcela':
            venda.dt_primeira_parcela,

        # =================================================
        # VALORES
        # =================================================

        'valor_total_formatado':
            valor_total_formatado,

        'valor_entrada_formatado':
            valor_entrada_formatado,

        'valor_sinal_formatado':
            valor_sinal_formatado,

        'valor_extenso':
            valor_extenso,

        'valor_desconto_formatado':
            valor_desconto_formatado,

        'valor_parcela_formatado':
            valor_parcela_formatado,

        'valor_financiado_formatado':
            valor_financiado_formatado,

        'valor_corrigido_formatado':
            valor_corrigido_formatado,

        # =================================================
        # PARCELAS
        # =================================================

        'total_parcelas':
            total_parcelas,

        # =================================================
        # CORREÇÃO
        # =================================================

        'correcao':
            correcao,

        'frase_reajuste':
            frase_reajuste,

        # =================================================
        # OBSERVAÇÃO
        # =================================================

        'observacao':
            venda.observacao,

    }

    html_final = template.render(
        Context(contexto)
    )

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

    # =====================================================
    # RESPONSE PDF
    # =====================================================

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="proposta_{venda.cliente.name}.pdf"'
    )

    # =====================================================
    # GERA PDF
    # =====================================================

    HTML(
        string=html_final
    ).write_pdf(

        response,

        stylesheets=[

            CSS(
                string='''

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
            )

        ]
    )

    return response


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
    enderecoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    contatoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    conjuge = ClienteConjuge.objects.filter(id=venda.cliente.id)

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
        'enderecoCliente': enderecoCliente,
        'contatoCliente': contatoCliente,
        'conjuge': conjuge,
        # 'cpf': venda.cliente.cpf,
        # 'lote': venda.lote.numero,
        # 'quadra': venda.lote.quadra.nome,
        # 'valor': venda.valor_total,
        # 'data': venda.data_venda.strftime('%d/%m/%Y'),
    }))

    return HttpResponse(html_final)


def contrato_pdf1(request):
    venda = get_object_or_404(RegisterVenda, id=request.GET.get('venda_id'))
    enderecoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    contatoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    conjuge = ClienteConjuge.objects.filter(id=venda.cliente.id)

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
        'enderecoCliente': enderecoCliente,
        'contatoCliente': contatoCliente,
        'conjuge': conjuge,
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
