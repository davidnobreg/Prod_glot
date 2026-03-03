import locale
from time import process_time_ns

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
from accounts.models import User


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

    clienteContato = None

    # Se existir venda, busca o telefone
    if venda:
        clienteContato = ClienteTelefone.objects.filter(
            cliente=venda.cliente
        ).first()

    # Se estiver vendido mas não existir venda registrada
    if lote.situacao.lower() == 'vendido' and venda is None:
        return render(request, 'reservado.html', {
            'lote': lote,
            'reservas': None,
            'contatoCliente': None
        })

    context = {
        'contatoCliente': clienteContato,
        'reservas': venda,
        'lote': lote
    }

    return render(request, 'reservado.html', context)


@has_permission_decorator('reservadoDetalhe')
def reservadoDetalhe(request, reserva_uuid):
    reservas = RegisterVenda.objects.filter(lote__uuid=reserva_uuid).first()
    contatoCorretor = User.objects.filter(first_name=reservas.corretor).first()
    context = {'reservas': reservas,
               'contatoCorretor': contatoCorretor}
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
    empreendimentos = Empreendimento.objects.filter(is_ativo=True).order_by('id')

    vendas = RegisterVenda.objects.filter(
        tipo_venda__in=['VENDIDO', 'CANCELADA'],
        is_ativo=False
    )

    filtros = {
        'venda': request.GET.get('venda'),
        'tipo_venda': request.GET.get('tipo_venda'),
        'tipo_empreendimento': request.GET.get('tipo_empreendimento'),
        'data_inicio': request.GET.get('data_inicio'),
        'data_fim': request.GET.get('data_fim'),
    }
    #print(venda)

    # Filtrar por empreendimento
    if filtros['tipo_empreendimento']:
        vendas = vendas.filter(
            lote__quadra__empr__id=filtros['tipo_empreendimento'],
            lote__quadra__empr__is_ativo=True
        )

    # Pesquisa textual
    if filtros['venda']:
        vendas = vendas.filter(
            Q(cliente__name__icontains=filtros['venda']) |
            #Q(cliente__fone__icontains=filtros['venda']) |
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
    """vendas = RegisterVenda.objects.filter(
        Q(user__icontains=request.user.first_name) |
        Q(is_ativo__icontains='False') |
        Q(tipo_venda__icontains='VENDIDO') |
        Q(tipo_venda__icontains='CANCELADA'))

    vendas = RegisterVenda.objects.filter(
        Q(user=request.user) |
        Q(is_ativo=False) |
        Q(tipo_venda__in=['VENDIDO', 'CANCELADA'])
    )"""
    if request.user.tipo_usuario == "ADMINISTRADOR":
        vendas = RegisterVenda.objects.filter(is_ativo=False)
    else:
        vendas = RegisterVenda.objects.filter(
            user=request.user
        )

    print(vendas)

    #contato = ClienteTelefone.objects.filter(id=vendas.cliente.id)


    get_data_venda = request.GET.get('venda')
    get_tipo_venda = request.GET.get('tipo_venda')

    if get_data_venda:  ## Filtra por nome, documento ou email do cliente
        vendas = RegisterVenda.objects.filter(
            Q(is_ativo__icontains='False') |
            Q(cliente__name__icontains=get_data_venda) |
            Q(cliente__fone__icontains=get_data_venda) |
            Q(lote__quadra__empr__nome__icontains=get_data_venda) |
            Q(user__username__icontains=get_data_venda)|
            Q(user=request.user)
        )

    if get_tipo_venda:
        vendas = RegisterVenda.objects.filter(tipo_venda=get_tipo_venda, user=request.user)



    paginator = Paginator(vendas.order_by('-id'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'vendas': page_obj}#,'contato': contato}

    return render(request, 'lista_venda_relatorio.html', context)


@has_permission_decorator('cancelarReservadoCadastro')
def cancelarReservadoCadastro(request, cancelaReserva_uuid):
    get_lote = get_object_or_404(Lote, uuid=cancelaReserva_uuid)

    print(get_lote)

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
def reserva_temporaria(request, lote_uuid):
    # 🔒 BUSCA ÚNICA + LOCK
    lote = (
        Lote.objects
        .select_for_update()
        .select_related('quadra__empr')
        .get(uuid=lote_uuid)
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
        #lote.situacao = "DISPONIVEL"
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
def criarReservado(request, reserva_uuid):
    get_lote = get_object_or_404(Lote, uuid=reserva_uuid)
    get_tempo = Empreendimento.objects.get(id=get_lote.quadra.empr_id)
    reserva_existente = RegisterVenda.objects.filter(lote=get_lote).first()

    corretor =  User.objects.filter(first_name=get_lote.user).first()

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

    """if request.method == 'GET':
        if not reserva_existente:
            get_lote.situacao = "PRE-RESERVA"#"EM_RESERVA"
            get_lote.tempo_reservado = timezone.now().time()
            get_lote.save()
            # print("Lote definido como EM_RESERVA.")
        form = RegisterVendaForm(empreendimento=get_tempo)  # inicializa form caso não seja post."""

    if request.method == 'GET':
        if not reserva_existente:
            get_lote.situacao = "PRE-RESERVA"
            get_lote.tempo_reservado = timezone.now().time()
            get_lote.save()

        form = RegisterVendaForm(
            user=request.user,
            empreendimento=get_tempo,
            lote=get_lote
        )

    if request.method == 'POST':

        # Se existir e estiver cancelada → editar
        if reserva_existente and reserva_existente.tipo_venda == 'CANCELADA':
            form = RegisterVendaForm(
                request.POST,
                instance=reserva_existente,
                user=request.user
            )

        # Se não existir → criar novo
        elif not reserva_existente:
            form = RegisterVendaForm(
                request.POST,
                user=request.user
            )

        # Se existir e não estiver cancelada → bloquear
        else:
            messages.error(request, "Já existe uma venda ativa para este lote.")
            return redirect('listar-quadras', id=get_lote.quadra.empr_id)

        if form.is_valid():

            reserva = form.save(commit=False)

            reserva.lote = get_lote
            is_admin = request.user.tipo_usuario == 'ADMINISTRADOR'

            if is_admin:
                reserva.user = form.cleaned_data.get('corretor')
            else:
                reserva.user = request.user
            reserva.tipo_venda = 'RESERVADO'
            reserva.is_ativo = False
            reserva.dt_reserva = timezone.now() + timedelta(days=get_tempo.tempo_reserva)
            reserva.valor_financiado = valor
            reserva.v = valor


            reserva.save()

            get_lote.situacao = "RESERVADO"
            get_lote.save()

            messages.success(request, "Reserva atualizada com sucesso!")
            return redirect('listar-quadras', id=get_lote.quadra.empr_id)

        else:
            messages.error(request, "Erro ao registrar reserva.")

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
def deleteVenda(request, delete_uuid):
    venda = RegisterVenda.objects.get(uuid=delete_uuid)
    loteSituação = Lote.objects.get(id=venda.lote.id)
    loteSituação.situacao = 'DISPONIVEL'
    venda.tipo_venda = 'CANCELADA'
    venda.is_ativo = True
    loteSituação.save()
    venda.save()
    messages.success(request, "Venda deletada com sucesso!")
    return redirect('listar-quadras', id=venda.lote.quadra.empr.id)
    # return redirect('lista-venda')


