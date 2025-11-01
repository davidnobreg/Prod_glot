from dateutil.tz import tzname_in_python2
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rolepermissions.decorators import has_permission_decorator

from datetime import datetime, timedelta
from django.utils import timezone
from django.core.paginator import Paginator

from .forms import RegisterVendaForm
from .models import RegisterVenda
from empreendimentos.models import Lote, Empreendimento



@has_permission_decorator('reservado')
def reservado(request, id):
    lote = get_object_or_404(Lote, pk=id)
    venda = RegisterVenda.objects.filter(lote=lote).first()

    # Verifica se o lote está marcado como vendido mas não possui venda registrada
    if lote.situacao.lower() == 'vendido' and venda is None:
        return render(request, 'reservado.html', {'lote': lote})

    # Caso contrário, segue para o template padrão
    context = {'reservas': venda,
               'lote':lote}
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

    # Empreendimento
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


    # 🔹 Filtro por intervalo de datas
    if get_data_inicio and get_data_fim:
        try:
            data_inicio = datetime.strptime(get_data_inicio, "%Y-%m-%d").date()
            data_fim = datetime.strptime(get_data_fim, "%Y-%m-%d").date()
            vendas = vendas.filter(dt_venda__range=[data_inicio, data_fim])
        except ValueError:
            pass
    elif get_data_inicio:
        vendas = vendas.filter(dt_venda__date__gte=get_data_inicio)
    elif get_data_fim:
        vendas = vendas.filter(dt_venda__date__lte=get_data_fim)

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

    context = {'vendas': vendas}
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
def criarVenda(request, id):
    venda = RegisterVenda.objects.get(id=id)
    lote = Lote.objects.get(id=venda.lote.id)
    venda.dt_venda = datetime.now()
    venda.tipo_venda = 'VENDIDO'
    lote.situacao = 'VENDIDO'
    lote.save()
    venda.save()
    messages.success(request, "Venda realizada com sucesso!")
    return redirect('listar-quadras', id=lote.quadra.empr_id)


@has_permission_decorator('renovarReserva')
def renovaReserva(request, id):
    get_venda = RegisterVenda.objects.get(id=id)
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
    venda = RegisterVenda.objects.get(lote=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    venda.tipo_venda = 'CANCELADA'
    venda.is_ativo = True
    loteSituação.save()
    venda.save()
    messages.success(request, "Venda deletada com sucesso!")
    return redirect('listar-quadras', id=venda.lote.quadra.empr_id)
    #return redirect('lista-venda')
