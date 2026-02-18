import os
from django.conf import settings
from django.template import Template, Context
from django.utils.timezone import now

from reportlab.platypus import Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import cm

from django.http import HttpResponse
from django.shortcuts import render
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

from .models import CadastroDocumento

def contrato_view(request):
    contrato = CadastroDocumento.objects.first()

    return render(
        request,
        'contratos/contrato.html',
        {'contrato': contrato}
    )

def contrato_pdf(request):
    contrato = CadastroDocumento.objects.first()

    template = Template(contrato.texto)
    texto_processado = template.render(Context(contexto))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="contrato.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=4 * cm,     # espaço para cabeçalho
        bottomMargin=3 * cm  # espaço para rodapé
    )

    # Informação usada no header
    doc.issue_date = now().strftime("%d/%m/%Y")

    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Contrato',
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    ))

    # Conteúdo do PDF
    story = []

    # Corpo do contrato (texto do CKEditor)
    paragrafos = contrato.texto.split('</p>')

    for p in paragrafos:
        p = p.replace('<p>', '').strip()
        if p:
            story.append(
                Paragraph(p, styles['Contrato'])
            )

    # Texto final jurídico
    story.append(Spacer(1, 40))
    story.append(
        Paragraph(
            "E, por estarem assim justas e contratadas, assinam o presente instrumento.",
            styles['Contrato']
        )
    )

    # Bloco de assinaturas
    story.append(Spacer(1, 50))
    story.append(bloco_assinaturas())

    # Geração do PDF com header e footer
    doc.build(
        story,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer
    )

    contexto = {
        "comprador_nome": "João da Silva",
        "comprador_cpf": "123.456.789-00",
        "comprador_endereco": "Rua Exemplo, 123",

        "lote_numero": "15",
        "quadra_nome": "B",
        "empreendimento_nome": "Residencial Jardim Vida",

        "valor_total": "150.000,00",
        "parcelas": "120"
    }

    return response


def draw_header_footer(canvas, doc):
    canvas.saveState()

    # 🔹 LOGO (opcional)
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')
    if os.path.exists(logo_path):
        canvas.drawImage(
            logo_path,
            2 * cm,
            27 * cm,
            width=3 * cm,
            preserveAspectRatio=True,
            mask='auto'
        )

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
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(
        A4[0] / 2,
        1.5 * cm,
        f"Página {doc.page}"
    )

    canvas.restoreState()

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
