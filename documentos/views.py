import locale
import os
from django.conf import settings
from django.template import Template, Context
from django.utils.timezone import now


from django.utils import timezone
from babel.dates import format_date

from reportlab.platypus import Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import cm

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

from .models import CadastroDocumento
from clientes.models import ClienteEndereco, ClienteTelefone, ClienteConjuge
from vendas.models import RegisterVenda


def contrato_view(request):
    contrato = CadastroDocumento.objects.first()

    return render(
        request,
        'contrato.html',
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


def proposta(request, venda_uuid):
    venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)

    enderecoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    contatoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    conjuge = ClienteConjuge.objects.filter(id=venda.cliente.id)

    # 🔥 REMOVIDO locale.setlocale

    data_atual = timezone.now().date()

    data_por_extenso = format_date(
        data_atual,
        format="d 'de' MMMM 'de' y",
        locale='pt_BR'
    )

    get_tempo = venda.lote.quadra.empr

    try:
        area = float(venda.lote.area)
        valor_metro = float(venda.lote.valor_metro_quadrado)
        valor = area * valor_metro
    except (TypeError, ValueError):
        valor = 0

    valor_total_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    try:
        total_parcelas = int(get_tempo.quantidade_parcela)
    except (TypeError, ValueError, AttributeError):
        total_parcelas = 0

    try:
        sinal = float(venda.valor_sinal)
        valor_financiado = (area * valor_metro) - sinal
    except (TypeError, ValueError):
        valor_financiado = 0

    valor_parcela = valor / total_parcelas if total_parcelas > 0 else 0

    valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_sinal_formatado = f"R$ {float(venda.valor_sinal):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_financiado_formatado = f"R$ {valor_financiado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    data_primeira_parcela = venda.dt_primeira_parcela

    documento = get_object_or_404(
        CadastroDocumento,
        id=1,
        ativo=True
    )

    template = Template(documento.texto)

    html_final = template.render(Context({
        'venda': venda,
        'data_por_extenso': data_por_extenso,
        'enderecoCliente': enderecoCliente,
        'telefoneCliente': contatoCliente,
        'valor_sinal_formatado': valor_sinal_formatado,
        'valor_total_formatado': valor_total_formatado,
        'valor_parcela_formatado': valor_parcela_formatado,
        'valor_financiado_formatado': valor_financiado_formatado,
        'data_primeira_parcela': data_primeira_parcela
    }))

    return HttpResponse(html_final)


def proposta_pdf(request, venda_uuid):
    venda = get_object_or_404(RegisterVenda, lote__uuid=request.GET.get('venda_uuid'))
    RegisterVenda.objects.filter(lote__uuid=reserva_uuid).first()
    enderecoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    contatoCliente = ClienteEndereco.objects.filter(id=venda.cliente.id)
    conjuge = ClienteConjuge.objects.filter(id=venda.cliente.id)

    # if not venda:
    #   raise Http404("Venda não informada")

    # try:
    #    venda = RegisterVenda.objects.get(id=venda_id)
    # except RegisterVenda.DoesNotExist:
    #    raise Http404("Venda não encontrada")

    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

    data_atual = timezone.now().date()

    data_por_extenso = format_date(
        data_atual,
        format="d 'de' MMMM 'de' y",
        locale='pt_BR'
    )

    get_tempo = venda.lote.quadra.empr

    # ======================
    # CÁLCULOS
    # ======================
    try:
        area = float(venda.lote.area)
        valor_metro = float(venda.lote.valor_metro_quadrado)
        valor = area * valor_metro
    except (TypeError, ValueError):
        valor = 0

    valor_total_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    try:
        total_parcelas = int(get_tempo.quantidade_parcela)
    except (TypeError, ValueError, AttributeError):
        total_parcelas = 0

    try:
        sinal = float(venda.valor_sinal)
        valor_metro = float(venda.lote.valor_metro_quadrado)
        valor_financiado = (area * valor_metro) - sinal
    except (TypeError, ValueError):
        valor_financiado = 0

    valor_parcela = valor / total_parcelas if total_parcelas > 0 else 0
    valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_sinal_formatado = f"R$ {float(venda.valor_sinal):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_financiado_formatado = f"R$ {valor_financiado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    data_primeira_parcela = venda.dt_primeira_parcela

    documento = get_object_or_404(
        CadastroDocumento,
        # tipo = 'venda'
        id=1,  # 🔥 aqui está a mágica
        ativo=True
    )

    template = Template(documento.texto)

    html_final = template.render(Context({
        'venda': venda,
        'nome_do_empreendimento': venda.lote.quadra.empr.nome,
        'quadra': venda.lote.quadra.namequadra,
        'lote': venda.lote.lote,
        'area': venda.lote.area,
        'cidade': venda.lote.quadra.empr.cidade,
        'cliente_nome': venda.cliente.name,
        'cliente_rg': venda.cliente.numero_rg,
        'cliente_rg_emissor': venda.cliente.orgao_emissor_rg,
        'cliente_cpf': venda.cliente.documento,
        'cliente_email': venda.cliente.email,
        'cliente_end': enderecoCliente,
        'cliente_cep': enderecoCliente,
        'cliente_telefone': contatoCliente,
        'corretor_nome': venda.user.first_name,
        'valor_sinal': venda.valor_sinal,
        'valor_financiado': venda.valor_inicio_contrato,
        'valor_venda': venda.valor_inicio_contrato,
        'valor_parcela_formatado': valor_parcela_formatado,
        'quantidade_parcelas': venda.quantidade_parcelas,
        'data_primeira_parcela': data_primeira_parcela,
        'data_por_extenso': data_por_extenso
    }))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="documento.pdf"'

    HTML(string=html_final).write_pdf(response)
    return response


"""def proposta(request):
    venda_id = request.GET.get('venda_id')

    if not venda_id:
        raise Http404("Venda não informada")

    try:
        venda = RegisterVenda.objects.get(id=venda_id)
    except RegisterVenda.DoesNotExist:
        raise Http404("Venda não encontrada")

    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

    enderecoCliente = ClienteEndereco.objects.filter(cliente=venda.cliente).first()
    telefoneCliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()

    data_atual = timezone.now().date()

    data_por_extenso = format_date(
        data_atual,
        format="d 'de' MMMM 'de' y",
        locale='pt_BR'
    )

    # 🔒 BUSCA ÚNICA + LOCK

    get_tempo = venda.lote.quadra.empr

    # ======================
    # CÁLCULOS
    # ======================
    try:
        area = float(venda.lote.area)
        valor_metro = float(venda.lote.valor_metro_quadrado)
        valor = area * valor_metro
    except (TypeError, ValueError):
        valor = 0

    valor_total_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    try:
        total_parcelas = int(get_tempo.quantidade_parcela)
    except (TypeError, ValueError, AttributeError):
        total_parcelas = 0

    try:
        sinal = float(venda.valor_sinal)
        valor_metro = float(venda.lote.valor_metro_quadrado)
        valor_financiado = (area * valor_metro) - sinal
    except (TypeError, ValueError):
        valor_financiado = 0

    valor_parcela = valor / total_parcelas if total_parcelas > 0 else 0
    valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_sinal_formatado = f"R$ {float(venda.valor_sinal):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_financiado_formatado = f"R$ {valor_financiado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    data_primeira_parcela = venda.dt_primeira_parcela

    context = {
        'venda': venda,
        'data_por_extenso': data_por_extenso,
        'enderecoCliente': enderecoCliente,
        'telefoneCliente': telefoneCliente,
        'valor_sinal_formatado': valor_sinal_formatado,
        'valor_total_formatado': valor_total_formatado,
        'valor_parcela_formatado': valor_parcela_formatado,
        'valor_financiado_formatado': valor_financiado_formatado,
        'data_primeira_parcela': data_primeira_parcela
    }
    return render(request, 'papeis/proposta.html', context)"""


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
        #tipo = 'venda',
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
