from dateutil.tz import tzname_in_python2
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q

from datetime import datetime, timedelta

from .forms import RegisterVendaForm
from .models import RegisterVenda
from empreendimentos.models import Lote, Quadra, Empreendimento



def reservado(request, id):
    reservas = RegisterVenda.objects.filter(lote_id=id).first()
    context = {'reservas': reservas}
    return render(request, 'reservado.html', context)


def lista_Reserva(request):
    reservas = RegisterVenda.objects.filter(tipo_venda='RESERVADO', is_ativo='False')
    #reservas = RegisterVenda.objects.all()

    get_localiza = request.GET.get('reserva')

    get_tipo_venda = request.GET.get('tipo_venda')

    get_data_reserva = request.GET.get('reserva')

    get_data_venda = request.GET.get('venda')

    if get_localiza:  ## Filtra por nome, documento ou email do cliente
        reservas = RegisterVenda.objects.filter(
            Q(cliente__name__icontains=get_localiza) |
            Q(lote__quadra__empr__nome__icontains=get_localiza)|
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




def lista_Venda(request):
    vendas = RegisterVenda.objects.filter(tipo_venda='VENDIDO', is_ativo='False')

    get_data_venda = request.GET.get('venda')
    get_tipo_venda = request.GET.get('tipo_venda')

    if get_data_venda:  ## Filtra por nome, documento ou email do cliente
        vendas = RegisterVenda.objects.filter(
            Q(is_ativo__icontains='False') |
            Q(cliente__name__icontains=get_data_venda) |
            Q(cliente__fone__icontains=get_data_venda) |
            Q(lote__quadra__empr__nome__icontains=get_data_venda)|
            Q(user__username__icontains=get_data_venda))

    if get_tipo_venda:
        vendas = RegisterVenda.objects.filter(tipo_venda=get_tipo_venda)


    context = {'vendas': vendas}
    return render(request, 'lista_venda.html', context)

def cancelar_Reservado_Cadastro(request, id):
    get_lote = get_object_or_404(Lote, id=id)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.save()
        messages.success(request, "Resevado cancelada!")
    return redirect('lista-empreendimento')

def cancelar_Reservado(request, id):
    get_venda = get_object_or_404(RegisterVenda, id=id)

    if request.method == 'GET':
        get_venda.lote.situacao = "DISPONIVEL"
        get_venda.tipo_venda = "CANCELADA"
        get_venda.lote.save()
        messages.success(request, "Resevado cancelada!")
    return redirect('lista-empreendimento')

def criar_Reservado(request, id):
    get_lote = get_object_or_404(Lote, id=id)
    get_tempo = Empreendimento.objects.get(id=get_lote.quadra.empr_id)


    if request.method == 'GET':
        # VERIFICAR STATOS DO LOTE ANTES DE FAZER O POST
        get_lote.situacao = "RESERVADO"
        get_lote.save()


    if request.method == 'POST':
       form = RegisterVendaForm(request.POST)

       if form.is_valid():
          reserva_form = form.save(commit=False)
          reserva_form.lote = get_lote
          reserva_form.user = request.user  # Define o usuário que está fazendo a venda
          reserva_form.tipo_venda = 'RESERVADO'
          reserva_form.dt_reserva = datetime.now() + timedelta(days=get_tempo.tempo_reseva)
          messages.success(request, "Reservado com sucesso!")
          reserva_form.save()

          get_lote.situacao = "RESERVADO"
          get_lote.save()

          messages.success(request, "Resevado com sucesso!")
          return redirect('lista-empreendimento')
       else:
          messages.error(request, "Erro ao registrar reserva.")
          get_lote.situacao = "DISPONIVEL"
          get_lote.save()

    else:
        form = RegisterVendaForm()

    context = {'form': form, 'lote': get_lote}
    return render(request, 'reserva.html', context)

def criar_Venda(request, id):
    venda = RegisterVenda.objects.get(id=id)
    lote = Lote.objects.get(id=venda.lote.id)
    venda.dt_venda = datetime.now()
    venda.tipo_venda = 'VENDIDO'
    lote.situacao = 'VENDIDO'
    lote.save()
    venda.save()
    messages.success(request, "Venda criada com sucesso!")
    return redirect('lista-reserva')


def renova_reserva(request, id):
    get_venda = RegisterVenda.objects.get(id=id)
    get_tempo = Empreendimento.objects.get(id=get_venda.lote.quadra.empr_id)

    get_venda.dt_reserva = datetime.now() + timedelta(days=get_tempo.tempo_reseva)

    get_venda.save()
    messages.success(request, "Reserva renovada com sucesso!")
    return redirect('lista-reserva')


def delete_reseva(request, id):
    venda = RegisterVenda.objects.get(id=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    loteSituação.save()
    venda.is_ativo = False
    venda.tipo_venda = 'CANCELADA'
    venda.save()
    messages.success(request, "Reserva deletada com sucesso!")
    return redirect('lista-reserva')


def delete_venda(request, id):
    venda = RegisterVenda.objects.get(id=id)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    venda.tipo_venda = 'CANCELADA'
    venda.is_ativo = True
    loteSituação.save()
    venda.save()
    messages.success(request, "Venda deletada com sucesso!")
    return redirect('lista-venda')
