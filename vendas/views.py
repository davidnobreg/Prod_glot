from dateutil.tz import tzname_in_python2
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rolepermissions.decorators import has_permission_decorator

from datetime import datetime, timedelta
from django.utils import timezone

from .forms import RegisterVendaForm
from .models import RegisterVenda
from empreendimentos.models import Lote, Empreendimento


@has_permission_decorator('reservado')
def reservado(request, id):
    reservas = RegisterVenda.objects.filter(lote_id=id).first()
    context = {'reservas': reservas}
    return render(request, 'reservado.html', context)

@has_permission_decorator('reservadoDetalhe')
def reservadoDetalhe(request, id):
    reservas = RegisterVenda.objects.filter(lote_id=id).first()
    context = {'reservas': reservas}
    return render(request, 'reservado_detalhe.html', context)

@has_permission_decorator('relatorioReserva')
def listaReserva(request):
    reservas = RegisterVenda.objects.filter(tipo_venda='RESERVADO', is_ativo='False')

    get_localiza = request.GET.get('reserva')

    get_tipo_venda = request.GET.get('tipo_venda')

    get_data_reserva = request.GET.get('reserva')

    get_data_venda = request.GET.get('venda')

    if get_localiza:  ## Filtra por nome, documento ou email do cliente
        reservas = RegisterVenda.objects.filter(
            Q(cliente__name__icontains=get_localiza) |
            Q(lote__quadra__empr__nome__icontains=get_localiza) |
            Q(user__username__icontains=get_localiza))

    if get_data_reserva:  ## Por data
        reservas = RegisterVenda.objects.filter(
            dt_reserva__icontains=get_data_reserva)

    if get_data_venda:  ## Por data
        reservas = RegisterVenda.objects.filter(
            dt_venda__icontains=get_data_venda)

    if get_tipo_venda:
        reservas = RegisterVenda.objects.filter(tipo_venda=get_tipo_venda)

    context = {'reservas': reservas}
    return render(request, 'lista_reserva.html', context)


@has_permission_decorator('relatorioVenda')
def listaVenda(request):
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
        get_lote.situacao = "DISPONIVEL"
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
        messages.success(request, "Resevado cancelada!")
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


    #print(f"Lote ID: {id}, Situação Inicial: {get_lote.situacao}")

    #  Libera automaticamente um lote travado em "EM_RESERVA" se não tiver reserva válida
    if get_lote.situacao == "EM_RESERVA" and not reserva_existente:
        get_lote.situacao = "DISPONIVEL"
        get_lote.save()
        #print("Liberando lote bloqueado sem reserva válida.")

    if request.method == 'GET':
        if not reserva_existente:
            get_lote.situacao = "EM_RESERVA"
            get_lote.tempo_reservado = timezone.now().time()
            get_lote.save()
            #print("Lote definido como EM_RESERVA.")
        form = RegisterVendaForm() #inicializa form caso não seja post.

    if request.method == 'POST':
        form = RegisterVendaForm(request.POST, instance=reserva_existente) if reserva_existente else RegisterVendaForm(request.POST)

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
            messages.success(request, "Lote reservado com sucesso!")
            return redirect('lista-empreendimento')
        else:
            messages.error(request, "Erro ao registrar reserva.")
            get_lote.situacao = "DISPONIVEL"
            get_lote.save()

    context = {'form': form , 'lote': get_lote, 'valor_formatado': valor_formatado}
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
    messages.success(request, "Venda criada com sucesso!")
    return redirect('lista-reserva')


@has_permission_decorator('renovarReserva')
def renovaReserva(request, id):
    get_venda = RegisterVenda.objects.get(id=id)
    get_tempo = Empreendimento.objects.get(id=get_venda.lote.quadra.empr_id)

    get_venda.dt_reserva = datetime.now() + timedelta(days=get_tempo.tempo_reseva)

    get_venda.save()
    messages.success(request, "Reserva renovada com sucesso!")
    return redirect('lista-reserva')


@has_permission_decorator('cancelarReservado')
def deleteReseva(request, id):
    venda = RegisterVenda.objects.get(id=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    loteSituação.save()
    venda.is_ativo = False
    venda.tipo_venda = 'CANCELADA'
    venda.save()
    messages.success(request, "Reserva deletada com sucesso!")
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
    return redirect('lista-venda')
