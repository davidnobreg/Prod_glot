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
from weasyprint import HTML




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

    venda = get_object_or_404(
        RegisterVenda,
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
        - sinal
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

    }))

    return HttpResponse(
        html_final
    )


def proposta_pdf(request, venda_uuid):

    venda = get_object_or_404(
        RegisterVenda,
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
    def moeda_para_float(valor):

        if not valor:
            return 0

        try:
            return float(
                str(valor)
                .replace('R$', '')
                .replace('.', '')
                .replace(',', '.')
                .strip()
            )

        except (TypeError, ValueError):
            return 0

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

        valor = area * valor_metro

    except (TypeError, ValueError):

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
    sinal = moeda_para_float(
        venda.valor_sinal
    )

    valor_financiado = (
        valor_corrigido - sinal
    )

    # ======================
    # VALOR PARCELA
    # ======================
    valor_parcela = (
        valor_financiado / total_parcelas
        if total_parcelas > 0 else 0
    )

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
            f"AS PARCELAS SERÃO CORRIGIDAS "
            f"PELO {tipo_reajuste}."
        )

    else:

        frase_reajuste = (
            "AS PARCELAS NÃO SERÃO "
            "CORRIGIDAS."
        )

    # ======================
    # FORMATADOS
    # ======================
    valor_total_formatado = (
        formatar_moeda_br(valor)
    )

    valor_entrada_formatado = (
        formatar_moeda_br(sinal)
    )

    valor_sinal_formatado = (
        formatar_moeda_br(sinal)
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

        # ======================
        # OBJETOS
        # ======================
        'venda':
            venda,

        'endereco_cliente':
            endereco_cliente,

        'contato_cliente':
            contato_cliente,

        'conjuge':
            conjuge,

        # ======================
        # EMPREENDIMENTO
        # ======================
        'nome_do_empreendimento':
            venda.lote.quadra.empr.nome,

        'cidade':
            venda.lote.quadra.empr.cidade,

        # ======================
        # LOTE
        # ======================
        'quadra':
            venda.lote.quadra.namequadra,

        'lote':
            venda.lote.lote,

        'area':
            venda.lote.area,

        # ======================
        # CLIENTE
        # ======================
        'cliente_nome':
            venda.cliente.name,

        'cliente_rg':
            venda.cliente.numero_rg,

        'cliente_rg_emissor':
            venda.cliente.orgao_emissor_rg,

        'cliente_cpf':
            venda.cliente.documento,

        'cliente_email':
            venda.cliente.email,

        # ======================
        # CORRETOR
        # ======================
        'corretor_nome':
            venda.user.first_name,

        # ======================
        # DATAS
        # ======================
        'data_por_extenso':
            data_por_extenso,

        'data_primeira_parcela':
            data_primeira_parcela,

        # ======================
        # VALORES
        # ======================
        'valor_entrada_formatado':
            valor_entrada_formatado,

        'valor_sinal_formatado':
            valor_sinal_formatado,

        'valor_total_formatado':
            valor_total_formatado,

        'valor_parcela_formatado':
            valor_parcela_formatado,

        'valor_financiado_formatado':
            valor_financiado_formatado,

        'valor_corrigido_formatado':
            valor_corrigido_formatado,

        # ======================
        # PARCELAS
        # ======================
        'total_parcelas':
            total_parcelas,

        'quantidade_parcelas':
            total_parcelas,

        # ======================
        # CORREÇÃO
        # ======================
        'correcao':
            correcao,

        'frase_reajuste':
            frase_reajuste,

    }))

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = 'inline; filename="documento.pdf"'

    HTML(
        string=html_final
    ).write_pdf(response)

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
