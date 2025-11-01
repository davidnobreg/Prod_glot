
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer



from rolepermissions.decorators import has_permission_decorator

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views import View

from django.utils import timezone
from datetime import datetime, timedelta

from tornado.http1connection import parse_int

from .forms import EmpreendimentoForm, ArquivoForm, LoteForm
from .models import Empreendimento, Quadra, Lote
from accounts.models import User, UsuarioEmpreendimento


@has_permission_decorator('selectEmpreendimento')
def selectEmpreendimento(request, empreendimento_id):
    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    data = {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
    }

    return JsonResponse(data)


@has_permission_decorator('criarEmpreendimento')
def criarEmpreendimento(request):
    form = EmpreendimentoForm()

    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                empreendimento = form.save()
                files = request.FILES.getlist('Empreendimento')

                imagens_criadas = []
                erros = []

                for file in files:
                    if file.content_type.startswith('image/'):
                        img = ImagemEmpreendimento(empreendimento=empreendimento, imagem=file)
                        try:
                            img.full_clean()  # Validações do Django
                            img.save()
                            imagens_criadas.append(file.name)
                        except ValidationError as e:
                            erros.append(f"Erro ao salvar {file.name}: {e}")
                    else:
                        erros.append(f"O arquivo {file.name} não é uma imagem válida.")

                # Exibir mensagens apropriadas
                if imagens_criadas:
                    messages.success(request,
                                     f"Empreendimento criado com sucesso! Imagens adicionadas: {', '.join(imagens_criadas)}")
                if erros:
                    messages.warning(request, "Algumas imagens não foram salvas:\n" + "\n".join(erros))

                return redirect('lista-empreendimento-tabela')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao criar o empreendimento: {e}")

    return render(request, 'empreendimento.html', {'form': form})


@has_permission_decorator('listaEmpreendimento')
def listaEmpreendimento(request):
    # Filtrando os empreendimentos que estão inativos e vinculados ao usuário logado
    empreendimentos_ids = UsuarioEmpreendimento.objects.filter(usuario=request.user, ativo=True).values_list(
        'empreendimento_id',
        flat=True)
    empreendimentos = Empreendimento.objects.filter(id__in=empreendimentos_ids, is_ativo=False)

    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos.html', context)


@has_permission_decorator('alterarEmpreendimento')
def alteraEmpreendimento(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)

    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES, instance=empreendimento)

        if form.is_valid():
            form.save()
            return redirect('lista-empreendimento-tabela')
        else:
            context = {'form': form, 'empreendimento': empreendimento}
            return render(request, 'update_empreendimento.html', context)
    else:
        form = EmpreendimentoForm(instance=empreendimento)
        context = {'form': form, 'empreendimento': empreendimento}
        return render(request, 'update_empreendimento.html', context)


@has_permission_decorator('deletarEmpreendimento')
@require_POST
def deleteEmpreendimento(request, empreendimento_Id):
    print(empreendimento_Id)
    empreendimento = Empreendimento.objects.get(id=empreendimento_Id)
    empreendimento.is_ativo = True
    empreendimento.save()
    return redirect('lista-empreendimento-tabela')


@has_permission_decorator('listaEmpreendimentoTabela')
def listaEmpreendimentoTabela(request):
    # Buscar empreendimentos que estão ativos
    empreendimentos = Empreendimento.objects.filter(is_ativo=False)

    get_empreendimento = request.GET.get('empreendimento')

    if get_empreendimento:
        empreendimentos = Empreendimento.objects.filter(nome=get_empreendimento)

    # Preparando os dados para exibição
    empreendimento_info = []

    for empreendimento in empreendimentos:
        # Lotes de cada empreendimento
        lotes = Lote.objects.filter(quadra__empr=empreendimento)

        total = lotes.count()
        livre = lotes.filter(situacao='DISPONIVEL').count()
        reservas = lotes.filter(situacao='RESERVADO').count()
        vendidos = lotes.filter(situacao='VENDIDO').count()
        outras = lotes.filter(
            Q(situacao='EM_RESERVA') |
            Q(situacao='CONSTRUTORA') |
            Q(situacao='INDISPONIVEL')
        ).count()

        # Adicionando as informações do empreendimento na lista
        empreendimento_info.append({
            'id': empreendimento.id,
            'nome': empreendimento.nome,
            'tempo_reserva': empreendimento.tempo_reserva,
            'quantidade_parcela': empreendimento.quantidade_parcela,
            'total': total,
            'livre': livre,
            'reservas': reservas,
            'vendidos': vendidos,
            'outras': outras,
        })

    context = {
        'empreendimentos': empreendimento_info,
    }
    return render(request, 'lista-empreendimentos-tabela.html', context)


@has_permission_decorator('listaQuadra')
def listaQuadra(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)
    situacao_filtro = request.GET.get('situacao')

    # Inicializa a consulta de quadras
    quadras = Quadra.objects.filter(empr=empreendimento).order_by('id')

    quadras_info_list = []

    for quadra in quadras:
        # Filtra os lotes diretamente aqui, com base na situação, se existir
        lotes = quadra.lotes.all()

        if situacao_filtro and situacao_filtro != 'TODOS':
            if situacao_filtro == 'OUTROS':
                lotes = lotes.filter(
                    Q(situacao='CONSTRUTORA') |
                    Q(situacao='EM_RESERVA') |
                    Q(situacao='INDISPONIVEL')
                )
            else:
                lotes = lotes.filter(situacao=situacao_filtro)

        # Se não houver lotes após o filtro, pula para a próxima quadra
        if not lotes.exists():
            continue

        total_livres = lotes.filter(situacao="DISPONIVEL").count()
        total_vendidos = lotes.filter(situacao="VENDIDO").count()
        outros = lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='EM_RESERVA') |
            Q(situacao='INDISPONIVEL')
        ).count()

        lotes_info = [{'lote': lote, 'situacao': lote.situacao} for lote in lotes]

        quadras_info_list.append({
            'quadra': quadra,
            'total_livres': total_livres,
            'total_vendidos': total_vendidos,
            'lotes': lotes_info,
            'outros': outros
        })

    # Paginação
    paginator = Paginator(quadras_info_list, 12)
    page = request.GET.get('page')

    try:
        quadras_info_page = paginator.page(page)
    except PageNotAnInteger:
        quadras_info_page = paginator.page(1)
    except EmptyPage:
        quadras_info_page = paginator.page(paginator.num_pages)

    # Estatísticas gerais
    all_lotes = Lote.objects.filter(quadra__empr=empreendimento)

    querydict = request.GET.copy()  # Torna o QueryDict mutável

    if 'page' in querydict:
        querydict.pop('page')  # Remove o parâmetro 'page'

    context = {
        'quadras_info': quadras_info_page,
        'empreendimento': empreendimento,
        'total': all_lotes.count(),
        'livre': all_lotes.filter(situacao='DISPONIVEL').count(),
        'prereserva': all_lotes.filter(situacao='PRE-RESERVA').count(),
        'reservado': all_lotes.filter(situacao='RESERVADO').count(),
        'vendido': all_lotes.filter(situacao='VENDIDO').count(),
        'outros': all_lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='INDISPONIVEL')
        ).count(),
        'situacao_filtro': situacao_filtro,
        'querystring': querydict.urlencode()
    }

    return render(request, 'lista-quadras.html', context)


class importarDados(View):
    template_name = 'empreendimento_arq.html'

    def get(self, request, id, *args, **kwargs):
        empreendimento = Empreendimento.objects.get(id=id)
        form = ArquivoForm()
        context = {'form': form, 'empreendimento': empreendimento}
        return render(request, self.template_name, context)

    def post(self, request, id):
        form = ArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['arquivo']

            # Lê o Excel a partir da terceira linha (pulando as duas primeiras)
            df = pd.read_excel(arquivo, skiprows=1,
                               names=["quadra", "lote", "area", "valor_metro_quadrado", "situacao"])

            # Remover linhas vazias
            df = df.dropna(subset=["quadra", "lote", "area", "valor_metro_quadrado"])

            # Converter os valores para string para evitar problemas
            df["quadra"] = df["quadra"].astype(str).str.strip()
            df["lote"] = df["lote"].astype(str).str.strip()

            # Iterar sobre as linhas do DataFrame e criar registros
            for _, row in df.iterrows():
                self.criar_quadra(row, id)
            messages.success(request, "Arquivo importado com sucesso!")
            return redirect('lista-empreendimento-tabela')  # Ajuste para onde quer redirecionar

        return render(request, self.template_name, {'form': form})

    def criar_quadra(self, row, id):
        quadra, _ = Quadra.objects.get_or_create(
            namequadra=row["quadra"],
            empr_id=id  # Supondo que 'empr' seja uma ForeignKey para 'empreendimento'
        )

        # Criar o lote com a situação original do arquivo
        Lote.objects.create(
            lote=row["lote"],
            area=row["area"],
            situacao=row["situacao"],  # Mantém o status real do lote
            valor_metro_quadrado=row["valor_metro_quadrado"],
            quadra=quadra
        )


def detalheEmpreendimento(request, id):
    template_name = 'detalhes-do-empreendimento.html'

    empreendimento = get_object_or_404(Empreendimento, id=id)

    usuarios = User.objects.all()
    empreendimentos = Empreendimento.objects.all()
    corretores = UsuarioEmpreendimento.objects.filter(empreendimento=id, ativo=True)

    lotes = Lote.objects.filter(quadra__empr=empreendimento)

    total = lotes.count()
    livre = lotes.filter(situacao='DISPONIVEL').count()
    reserva = lotes.filter(situacao='RESERVADO').count()
    vendido = lotes.filter(situacao='VENDIDO').count()
    outros = lotes.filter(
        Q(situacao='CONSTRUTORA') |
        Q(situacao='EM_RESERVA') |
        Q(situacao='INDISPONIVEL')
    ).count()

    context = {
        'empreendimento': empreendimento,
        'empreendimentos': empreendimentos,  # <- necessário para o <select>
        'usuarios': usuarios,
        'corretores': corretores,
        'total': total,
        'livre': livre,
        'reserva': reserva,
        'vendido': vendido,
        'outros': outros
    }

    return render(request, template_name, context)


from collections import OrderedDict
import math


def relatorioFinanceiro(request, id):
    template_name = 'relatorio-financeiro.html'

    empreendimento = Empreendimento.objects.get(id=id)

    lotes = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO') | Q(situacao='VENDIDO'))
    lotes_disponiveis = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO')
        )
    lotes_vendidos = Lote.objects.filter(quadra__empr_id=id, situacao='VENDIDO')

    quantidade_lotes = Lote.objects.filter(quadra__empr_id=id).count()
    quantidade_lotes_disponivel = Lote.objects.filter(quadra__empr_id=id).filter(
        Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO')).count()
    quantidade_lotes_vendidos = Lote.objects.filter(quadra__empr_id=id, situacao='VENDIDO').count()
    quantidade_lotes_indisponivel = Lote.objects.filter(quadra__empr_id=id).filter(
        Q(situacao='CONSTRUTORA') | Q(situacao='INDISPONIVEL')).count()

    data_atual = timezone.now()

    valor_total = 0

    for lote in lotes:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total += valor_lote

    parcelas_total = valor_total / empreendimento.quantidade_parcela

    # Formatar o valor total para moeda brasileira
    valor_total_formatado = f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    parcelas_total_formatado = f"R$ {parcelas_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    valor_total_disponivel = 0

    for lote in lotes_disponiveis:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total_disponivel += valor_lote

    parcelas_total_disponivel = valor_total_disponivel / empreendimento.quantidade_parcela

    valor_total_disponivel_formatado = f"R$ {valor_total_disponivel:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", ".")

    parcelas_total_disponivel_formatado = f"R$ {parcelas_total_disponivel :,.2f}".replace(",", "X").replace(".",
                                                                                                            ",").replace(
        "X", ".")

    valor_total_vendidos = 0

    for lote in lotes_vendidos:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total_vendidos += valor_lote

    parcelas_total_vendidos = valor_total_vendidos / empreendimento.quantidade_parcela

    valor_total_vendidos_formatado = f"R$ {valor_total_vendidos:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", ".")

    parcelas_total_vendidos_formatado = f"R$ {parcelas_total_vendidos :,.2f}".replace(",", "X").replace(".",
                                                                                                        ",").replace(
        "X", ".")

    # Exemplo de retorno ou envio para o template

    context = {
        'data_atual': data_atual,
        'empreendimento': empreendimento,
        'quantidade_lotes': quantidade_lotes,
        'quantidade_lotes_disponivel': quantidade_lotes_disponivel,
        'quantidade_lotes_vendidos': quantidade_lotes_vendidos,
        'quantidade_lotes_indisponivel': quantidade_lotes_indisponivel,
        'valor_total_formatado': valor_total_formatado,
        'parcelas_total_formatado': parcelas_total_formatado,
        'valor_total_disponivel_formatado': valor_total_disponivel_formatado,
        'parcelas_total_disponivel_formatado': parcelas_total_disponivel_formatado,
        'valor_total_vendidos_formatado': valor_total_vendidos_formatado,
        'parcelas_total_vendidos_formatado': parcelas_total_vendidos_formatado,
    }

    return render(request, template_name, context)


@has_permission_decorator('reservarLote')
def alteraLote(request, id):
    lote = get_object_or_404(Lote, id=id)
    get_tempo = Empreendimento.objects.get(id=lote.quadra.empr_id)

    #print(get_tempo.quantidade_parcela)

    try:
        area = float(lote.area)
        valor_metro = float(lote.valor_metro_quadrado)
        valor = area * valor_metro
    except (TypeError, ValueError):
        valor = 0

    # Formatação para moeda brasileira
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Pegando a quantidade de parcelas (ajuste o nome conforme seu modelo)
    try:
        total_parcelas = int(get_tempo.quantidade_parcela)
    except (TypeError, ValueError, AttributeError):
        total_parcelas = 0

    # Cálculo do valor da parcela
    if total_parcelas > 0:
        valor_parcela = valor / total_parcelas
    else:
        valor_parcela = 0

    # Formatação do valor da parcela
    valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Caso especial: liberar lote se estiver em reserva mas sem lógica de uso (defensivo)
    if lote.situacao == "EM_RESERVA" and not lote.user:
        lote.situacao = "DISPONIVEL"
        lote.save()
        messages.error(request, "Pre-Reservado Cancelada!")
        # print("Liberando lote bloqueado sem reserva válida.")

    if request.method == 'GET':
        # Ao acessar, define como EM_RESERVA
        if lote.situacao == "DISPONIVEL":
            lote.situacao = "EM_RESERVA"
            lote.tempo_reservado = timezone.now().time()
            lote.save()
            #print("Lote definido como EM_RESERVA.")
        form = LoteForm(instance=lote)
        context = {'form': form,
                   'lote': lote,
                   'valor_formatado': valor_formatado,
                   'valor_parcela_formatado': valor_parcela_formatado,
                   'total_parcelas': total_parcelas}
        return render(request, 'reserva-temporaria.html', context)

    elif request.method == 'POST':
        form = LoteForm(request.POST, request.FILES, instance=lote)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.situacao = 'PRE-RESERVA'
            lote.data_termina_reserva = timezone.now() + timedelta(days=lote.quadra.empr.tempo_reserva)
            lote.user = request.user.first_name
            lote.telefone_user = request.user.contato
            lote.save()
            messages.success(request, "Pre-Reservado Salva Com Sucesso!")
            return redirect('listar-quadras', id=lote.quadra.empr_id)
            #print("Lote salvo como PRE-RESERVA.")
        else:
            context = {'form': form,
                       'lote': lote,
                       'valor_formatado': valor_formatado,
                       'valor_parcela_formatado': valor_parcela_formatado,
                       'total_parcelas': total_parcelas}
            return render(request, 'reserva-temporaria.html', context)


@has_permission_decorator('reservadoDetalheEmpreendimento')
def reservadoDetalheEmpreendimento(request, id):
    lote = Lote.objects.filter(id=id).first()

    context = {'lote': lote}
    return render(request, 'detalhes-reserva-lote.html', context)


@has_permission_decorator('listaReservasTemporaria')
def listaReservasTemporaria(request):
    query = request.GET.get('q', '')
    tipo_empreendimento = request.GET.get('tipo_empreendimento', '')

    # Filtra lotes 'PRE-RESERVA'
    lotes = Lote.objects.filter(situacao='PRE-RESERVA')

    if query:
        lotes = lotes.filter(
            Q(quadra__empr__nome__icontains=query) |
            Q(quadra__nome__icontains=query) |
            Q(numero__icontains=query) |
            Q(user__username__icontains=query)
        )

    if tipo_empreendimento:
        lotes = lotes.filter(quadra__empr__id=tipo_empreendimento)

    paginator = Paginator(lotes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    empreendimentos = Empreendimento.objects.filter(is_ativo=False).order_by('id')

    context = {
        'page_obj': page_obj,
        'query': query,
        'tipo_empreendimento': tipo_empreendimento,
        'empreendimentos': empreendimentos,
    }
    return render(request, 'relatorio_de_reservas_temporario.html', context)


#@has_permission_decorator('liberaLote')
def liberaLote(request, id):
    get_lote = get_object_or_404(Lote, id=id)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.save()
        messages.success(request, "Lote liberado com Sucesso!")
    return redirect('listar-quadras', id=get_lote.quadra.empr_id)

@has_permission_decorator('cancelarReservadoTemporaria')
def cancelarReservadoTemporaria(request, id):
    get_lote = get_object_or_404(Lote, id=id)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.cliente_reserva = ""
        get_lote.telefone = ""
        get_lote.save()
        messages.error(request, "Pre-Resevado Cancelada!")
    return redirect('listar-quadras', id=get_lote.quadra.empr_id)

@has_permission_decorator('cancelarReservadoTemporariaLista')
def cancelarReservadoTemporariaLista(request, id):
    get_lote = get_object_or_404(Lote, id=id)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.cliente_reserva = ""
        get_lote.telefone = ""
        get_lote.save()
        messages.error(request, "Pre-Resevado Cancelada!")
    return redirect('lista-pre-reserva')


@has_permission_decorator('renovarReservaTemporaria')
def renovaReserva(request, id):
    get_lote = Lote.objects.get(id=id)

    get_lote.data_termina_reserva = datetime.now() + timedelta(days=get_lote.quadra.empr.tempo_reserva)

    get_lote.save()
    messages.success(request, "Reserva renovada com sucesso!")
    return redirect('lista-pre-reserva')

def gerarRelatorioLotes(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_lotes.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elementos = []

    # Filtros
    situacao = request.GET.get('situacao', 'TODOS')
    loteamento_id = request.GET.get('loteamento_id')

    # Aplica os filtros
    lotes = Lote.objects.all()
    if loteamento_id:
        lotes = lotes.filter(quadra__empr__id=loteamento_id)
    if situacao != 'TODOS':
        lotes = lotes.filter(situacao=situacao)

    # Verifica se há pelo menos um lote
    primeiro_lote = lotes.first()
    nome_empreendimento = primeiro_lote.quadra.empr.nome if primeiro_lote else "Empreendimento não identificado"

    # Título
    titulo = Paragraph(f"Relatório de Lotes - <b>{nome_empreendimento}</b>", styles['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    # Subtítulo
    subtitulo = Paragraph(f"Situação dos Lotes: <b>{situacao}</b>", styles['Heading2'])
    elementos.append(subtitulo)
    elementos.append(Spacer(1, 12))

    # Cabeçalho da tabela
    dados = [['Quadra', 'Lote', 'Situação', 'Vencimento da Reserva']]

    for lote in lotes:
        dados.append([
            lote.quadra.namequadra,
            lote.lote,
            lote.situacao,
            lote.data_termina_reserva.strftime('%d/%m/%Y') if lote.data_termina_reserva else ''
        ])

    # Tabela formatada
    tabela = Table(dados, colWidths=[90, 90, 120, 180])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#036B91")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (1, 1), (-1, -1), 6),
    ]))

    elementos.append(tabela)
    doc.build(elementos)
    return response

@require_http_methods(["POST"])
def criarUsuarioEmpreendimento(request):
    users_ids = request.POST.getlist('users')  # Lista de usuários
    empreendimento_id = request.POST.get('empreendimento')

    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    for user_id in users_ids:
        usuario = get_object_or_404(User, id=user_id)

        usuario_empreendimento, created = UsuarioEmpreendimento.objects.get_or_create(
            usuario=usuario,
            empreendimento=empreendimento,
            defaults={'ativo': True}
        )

        if not created:
            usuario_empreendimento.ativo = True
            usuario_empreendimento.save()

    messages.success(request, "Usuários adicionados com sucesso!")
    return redirect('detalhe-empreendimento', id=empreendimento.id)