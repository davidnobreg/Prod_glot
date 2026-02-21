import locale
from dateutil.tz import tzname_in_python2
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.template import Template, Context
from django.http import HttpResponse

from django.db.models import Q
from pygments.styles.dracula import pink
from rolepermissions.decorators import has_permission_decorator
from weasyprint import HTML

from datetime import datetime, timedelta
from django.utils import timezone
from babel.dates import format_date

from django.core.paginator import Paginator

from .forms import RegisterVendaForm
from clientes.models import ClienteEndereco, ClienteTelefone, ClienteConjuge
from .models import RegisterVenda
from documentos.models import CadastroDocumento
from empreendimentos.models import Lote, Empreendimento
from empreendimentos.forms import LoteForm


@has_permission_decorator('selectVenda')
def selectVenda(request, venda_id):
    venda = get_object_or_404(RegisterVenda, id=venda_id)

    data = {
        "empreendimento": venda.lote.quadra.empr,
        "quadra": venda.lote.quadra,
        "lote": venda.lote,
        "cliente": venda.cliente,
    }

    return JsonResponse(data)


@has_permission_decorator('reservado')
def reservado(request, uuid):
    lote = get_object_or_404(Lote, uuid=uuid)
    venda = RegisterVenda.objects.filter(lote=lote).first()
    clienteContato = ClienteTelefone.objects.filter(cliente=venda.cliente).first()


    # Verifica se o lote está marcado como vendido mas não possui venda registrada
    if lote.situacao.lower() == 'vendido' and venda is None:
        return render(request, 'reservado.html', {'lote': lote})

    # Caso contrário, segue para o template padrão
    context = {
        'contatoCliente': clienteContato,
        'reservas': venda,
        'lote': lote}
    return render(request, 'reservado.html', context)


@has_permission_decorator('reservadoDetalhe')
def reservadoDetalhe(request, id):
    reservas = RegisterVenda.objects.filter(lote_id=id).first()
    context = {'reservas': reservas}
    return render(request, 'reservado_detalhe.html', context)


@has_permission_decorator('relatorioReserva')
def listaReserva(request):
    empreendimentos = Empreendimento.objects.filter(is_ativo=False).order_by('id')
    reservas = RegisterVenda.objects.filter(tipo_venda='RESERVADO', is_ativo=False)

    # Pegando filtros
    filtro_empreendimento = request.GET.get('tipo_empreendimento')
    filtro_nome = request.GET.get('search_nome')
    filtro_tipo_venda = request.GET.get('tipo_venda')
    filtro_data_reserva = request.GET.get('data_reserva')
    filtro_data_venda = request.GET.get('data_venda')

    # Aplicando filtros
    if filtro_empreendimento and filtro_empreendimento.isdigit():
        reservas = reservas.filter(lote__quadra__empr__id=int(filtro_empreendimento))

    if filtro_nome:
        reservas = reservas.filter(
            Q(cliente__name__icontains=filtro_nome) |
            Q(lote__quadra__empr__nome__icontains=filtro_nome) |
            Q(user__username__icontains=filtro_nome)
        )

    if filtro_data_reserva:
        try:
            data = datetime.strptime(filtro_data_reserva, "%Y-%m-%d").date()
            reservas = reservas.filter(dt_reserva=data)
        except ValueError:
            pass

    if filtro_data_venda:
        try:
            data = datetime.strptime(filtro_data_venda, "%Y-%m-%d").date()
            reservas = reservas.filter(dt_venda=data)
        except ValueError:
            pass

    if filtro_tipo_venda:
        reservas = reservas.filter(tipo_venda=filtro_tipo_venda)

    # Paginação
    paginator = Paginator(reservas, 10)  # Exibe 10 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'reservas': page_obj,
        'empreendimentos': empreendimentos,
    }
    return render(request, 'lista_reserva.html', context)


@has_permission_decorator('relatorioVenda')
def listaVenda(request):
    empreendimentos = Empreendimento.objects.filter(is_ativo=False).order_by('id')

    vendas = RegisterVenda.objects.exclude(tipo_venda='RESERVADO').filter(
        Q(is_ativo=False) | Q(tipo_venda__in=['VENDIDO', 'CANCELADA'])
    )

    filtros = {
        'venda': request.GET.get('venda'),
        'tipo_venda': request.GET.get('tipo_venda'),
        'tipo_empreendimento': request.GET.get('tipo_empreendimento'),
        'data_inicio': request.GET.get('data_inicio'),
        'data_fim': request.GET.get('data_fim'),
    }

    # Filtrar por empreendimento
    if filtros['tipo_empreendimento']:
        vendas = vendas.filter(lote__quadra__empr__id=filtros['tipo_empreendimento'])

    # Pesquisa textual
    if filtros['venda']:
        vendas = vendas.filter(
            Q(cliente__name__icontains=filtros['venda']) |
            Q(cliente__fone__icontains=filtros['venda']) |
            Q(lote__quadra__empr__nome__icontains=filtros['venda']) |
            Q(user__username__icontains=filtros['venda'])
        )

    # Tipo de venda
    if filtros['tipo_venda']:
        vendas = vendas.filter(tipo_venda=filtros['tipo_venda'])

    # Filtro por intervalo de datas
    data_inicio = filtros['data_inicio']
    data_fim = filtros['data_fim']

    try:
        if data_inicio and data_fim:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            vendas = vendas.filter(dt_venda__range=[dt_inicio, dt_fim])
        elif data_inicio:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            vendas = vendas.filter(dt_venda__date__gte=dt_inicio)
        elif data_fim:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            vendas = vendas.filter(dt_venda__date__lte=dt_fim)
    except ValueError:
        pass

    paginator = Paginator(vendas.order_by('-id'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'vendas': page_obj,
        'empreendimentos': empreendimentos,
    }
    return render(request, 'lista_venda.html', context)


@has_permission_decorator('listaVendaRelatorio')
def listaVendaRelatorio(request):
    vendas = RegisterVenda.objects.filter(
        Q(is_ativo__icontains='False') |
        Q(tipo_venda__icontains='VENDIDO') |
        Q(tipo_venda__icontains='CANCELADA'))

    get_data_venda = request.GET.get('venda')
    get_tipo_venda = request.GET.get('tipo_venda')

    if get_data_venda:  ## Filtra por nome, documento ou email do cliente
        vendas = RegisterVenda.objects.filter(
            Q(is_ativo__icontains='False') |
            Q(cliente__name__icontains=get_data_venda) |
            Q(cliente__fone__icontains=get_data_venda) |
            Q(lote__quadra__empr__nome__icontains=get_data_venda) |
            Q(user__username__icontains=get_data_venda))

    if get_tipo_venda:
        vendas = RegisterVenda.objects.filter(tipo_venda=get_tipo_venda)

    paginator = Paginator(vendas.order_by('-id'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'vendas': page_obj}
    return render(request, 'lista_venda_relatorio.html', context)


@has_permission_decorator('cancelarReservadoCadastro')
def cancelarReservadoCadastro(request, id):
    get_lote = get_object_or_404(Lote, id=id)

    if request.method == 'GET':
        get_lote.situacao = "PRE-RESERVA"
        get_lote.save()
        messages.success(request, "Resevado cancelada!")
    return redirect('lista-empreendimento')


@has_permission_decorator('cancelarReservado')
def cancelarReservado(request, id):
    get_venda = get_object_or_404(RegisterVenda, id=id)

    if request.method == 'GET':
        get_venda.lote.situacao = "DISPONIVEL"
        get_venda.tipo_venda = "CANCELADA"
        get_venda.lote.save()
        messages.error(request, "Pre-Resevado Cancelada!")
    return redirect('lista-empreendimento')


@transaction.atomic
def reserva_temporaria(request, lote_id):
    # 🔒 BUSCA ÚNICA + LOCK
    lote = (
        Lote.objects
        .select_for_update()
        .select_related('quadra__empr')
        .get(id=lote_id)
    )

    get_tempo = lote.quadra.empr

    # ======================
    # CÁLCULOS
    # ======================
    try:
        area = float(lote.area)
        valor_metro = float(lote.valor_metro_quadrado)
        valor = area * valor_metro
    except (TypeError, ValueError):
        valor = 0

    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    try:
        total_parcelas = int(get_tempo.quantidade_parcela)
    except (TypeError, ValueError, AttributeError):
        total_parcelas = 0

    valor_parcela = valor / total_parcelas if total_parcelas > 0 else 0
    valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ======================
    # DEFENSIVO (DENTRO DO LOCK)
    # ======================
    if lote.situacao == "EM_RESERVA" and not lote.user:
        lote.situacao = "DISPONIVEL"
        lote.tempo_reservado = None
        lote.save()
        messages.error(request, "Pré-reserva cancelada automaticamente.")

    # ======================
    # GET → RESERVA TEMPORÁRIA
    # ======================
    if request.method == 'GET':
        if lote.situacao == "DISPONIVEL":
            lote.situacao = "EM_RESERVA"
            lote.tempo_reservado = timezone.now()
            lote.save()
        else:
            messages.warning(
                request,
                "Este lote já está em reserva ou indisponível."
            )
            return redirect('lotes_disponiveis')

        form = LoteForm(instance=lote)

        return render(
            request,
            'reserva-temporaria.html',
            {
                'form': form,
                'lote': lote,
                'valor_formatado': valor_formatado,
                'valor_parcela_formatado': valor_parcela_formatado,
                'total_parcelas': total_parcelas,
            }
        )

    # ======================
    # POST → PRÉ-RESERVA
    # ======================
    elif request.method == 'POST':
        form = LoteForm(request.POST, request.FILES, instance=lote)

        if form.is_valid():
            lote = form.save(commit=False)
            lote.situacao = 'PRE-RESERVA'
            lote.data_termina_reserva = timezone.now() + timedelta(
                days=get_tempo.tempo_reserva
            )
            lote.user = request.user.first_name
            lote.telefone_user = request.user.contato
            lote.save()

            messages.success(request, "Pré-reserva salva com sucesso!")
            return redirect('listar-quadras', id=get_tempo.id)

        return render(
            request,
            'reserva-temporaria.html',
            {
                'form': form,
                'lote': lote,
                'valor_formatado': valor_formatado,
                'valor_parcela_formatado': valor_parcela_formatado,
                'total_parcelas': total_parcelas,
            }
        )


@has_permission_decorator('criarReservado')
@transaction.atomic
def criarReservado(request, id):
    get_lote = get_object_or_404(Lote, id=id)
    get_tempo = Empreendimento.objects.get(id=get_lote.quadra.empr_id)
    reserva_existente = RegisterVenda.objects.filter(lote=get_lote).first()

    try:
        area = float(get_lote.area)
        valor_metro = float(get_lote.valor_metro_quadrado)
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

    # Exibir os valores formatados
    # print(f"Valor total: {valor}")
    # print(f"Valor total: {valor_formatado}")
    # print(f"Valor da parcela: {valor_parcela_formatado}")
    # print(f"Lote ID: {id}, Situação Inicial: {get_lote.situacao}")

    #  Libera automaticamente um lote travado em "EM_RESERVA" se não tiver reserva válida
    if get_lote.situacao == "EM_RESERVA" and not reserva_existente:
        get_lote.situacao = "PRE-RESERVA"
        get_lote.save()
        # print("Liberando lote bloqueado sem reserva válida.")

    if request.method == 'GET':
        if not reserva_existente:
            get_lote.situacao = "EM_RESERVA"
            get_lote.tempo_reservado = timezone.now().time()
            get_lote.save()
            # print("Lote definido como EM_RESERVA.")
        form = RegisterVendaForm()  # inicializa form caso não seja post.

    if request.method == 'POST':
        form = RegisterVendaForm(request.POST, instance=reserva_existente) if reserva_existente else RegisterVendaForm(
            request.POST)

        if form.is_valid():
            cliente = form.cleaned_data.get('cliente')
            if not cliente:
                messages.error(request, "Cliente inválido. Informe um cliente válido.")
                return redirect('criar-reservado', id=id)

            reserva_form = form.save(commit=False)
            reserva_form.lote = get_lote
            reserva_form.user = request.user
            reserva_form.tipo_venda = 'RESERVADO'
            reserva_form.is_ativo = False
            reserva_form.dt_reserva = timezone.now() + timedelta(days=get_tempo.tempo_reserva)
            reserva_form.quantidade_parcelas = total_parcelas
            reserva_form.valor_inicio_contrato = valor
            reserva_form.valor_financiado = valor
            reserva_form.save()

            get_lote.situacao = "RESERVADO"
            get_lote.save()
            messages.success(request, "Reservado com sucesso!")
            return redirect('listar-quadras', id=get_lote.quadra.empr_id)
        else:
            messages.error(request, "Erro ao registrar reserva.")
            get_lote.situacao = "PRE-RESERVA"
            get_lote.save()

    context = {'form': form,
               'lote': get_lote,
               'valor_formatado': valor_formatado,
               'valor_parcela_formatado': valor_parcela_formatado,
               'total_parcelas': total_parcelas}
    return render(request, 'reserva.html', context)


@has_permission_decorator('criarVenda')
def criarVenda(request, venda_uuid):
    venda = RegisterVenda.objects.get(uuid=venda_uuid)
    lote = Lote.objects.get(id=venda.lote.id)
    venda.dt_venda = datetime.now()
    venda.tipo_venda = 'VENDIDO'
    lote.situacao = 'VENDIDO'
    lote.save()
    venda.save()
    messages.success(request, "Venda realizada com sucesso!")
    return redirect('listar-quadras', id=lote.quadra.empr_id)


@has_permission_decorator('renovarReserva')
def renovaReserva(request, venda_uuid):
    get_venda = RegisterVenda.objects.get(uuid=venda_uuid)
    get_tempo = Empreendimento.objects.get(id=get_venda.lote.quadra.empr_id)

    get_venda.dt_reserva = datetime.now() + timedelta(days=get_tempo.tempo_reserva)

    get_venda.save()
    messages.success(request, "Reserva renovada com sucesso!")
    return redirect('listar-quadras', id=get_venda.lote.quadra.empr_id)


@has_permission_decorator('cancelarReservado')
def deleteReseva(request, id):
    venda = RegisterVenda.objects.get(id=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    loteSituação.save()
    venda.is_ativo = False
    venda.tipo_venda = 'CANCELADA'
    venda.save()
    messages.error(request, "Reserva Cancelada com sucesso!")
    return redirect('listar-quadras', id=loteSituação.quadra.empr_id)


@has_permission_decorator('cancelarReservado')
def deleteResevaLista(request, id):
    venda = RegisterVenda.objects.get(id=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    loteSituação.save()
    venda.is_ativo = False
    venda.tipo_venda = 'CANCELADA'
    venda.save()
    messages.error(request, "Reserva Cancelada com sucesso!")
    return redirect('lista-reserva')


@has_permission_decorator('cancelarVenda')
def deleteVenda(request, id):
    venda = RegisterVenda.objects.get(id=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    venda.tipo_venda = 'CANCELADA'
    venda.is_ativo = True
    loteSituação.save()
    venda.save()
    messages.success(request, "Venda deletada com sucesso!")
    return redirect('listar-quadras', id=venda.lote.quadra.empr_id)
    # return redirect('lista-venda')


def proposta(request, venda_uuid):
    venda = get_object_or_404(RegisterVenda, uuid=venda_uuid) #request.GET.get('venda_uuid'))
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


def proposta_pdf(request):
    venda = get_object_or_404(RegisterVenda, id=request.GET.get('venda_id'))
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


def visualizar_documento(request, venda_uuid):
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


def documento_pdf(request):
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
