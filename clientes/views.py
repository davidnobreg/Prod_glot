import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from rolepermissions.decorators import has_permission_decorator

from .forms import ClienteForm, ClienteConjugeForm, ClienteEnderecoForm, ClienteTelefoneForm
from .models import Cliente, ClienteConjuge, ClienteEndereco, ClienteTelefone



@has_permission_decorator('selectCliente')
def selectCliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    data = {
        "id": cliente.id,
        "name": cliente.name,
        "documento": cliente.documento,
        "email": cliente.email,
        "fone": cliente.fone,
    }

    return JsonResponse(data)



@has_permission_decorator('criarCliente')
def criarCliente(request):
    lote_id = request.GET.get('lote_id') or request.POST.get('lote_id')
    previous = request.META.get('HTTP_REFERER', '')
    veio_da_lista = '/clientes/listar_clientes/' in previous

    if request.method == 'POST':
        form = ClienteForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Verifique os campos obrigatórios.")
            return render(request, 'cliente.html', {
                'form': form,
                'formConjuge': ClienteConjugeForm(),
                'formEndereco': ClienteEnderecoForm(),
                'formTelefone': ClienteTelefoneForm(),
                'veio_da_lista': veio_da_lista,
                'lote_id': lote_id,
            })

        # =========================
        # 1️⃣ Salvar Cliente
        # =========================
        cliente = form.save()

        # =========================
        # 2️⃣ Salvar Endereço (JSON)
        # =========================
        endereco_json = request.POST.get('endereco_json')
        if endereco_json:
            try:
                endereco_data = json.loads(endereco_json)
                ClienteEndereco.objects.create(
                    cliente=cliente,
                    cep=endereco_data.get('cep', ''),
                    rua=endereco_data.get('rua', ''),
                    numero=endereco_data.get('numero', ''),
                    complemento=endereco_data.get('complemento', ''),
                    bairro=endereco_data.get('bairro', ''),
                    cidade=endereco_data.get('cidade', ''),
                    estado=endereco_data.get('estado', ''),
                    is_ativo=True
                )
            except json.JSONDecodeError:
                messages.warning(request, "Endereço inválido. Não foi possível salvar.")

        # =========================
        # 3️⃣ Salvar Telefones (JSON)
        # =========================
        telefones_json = request.POST.get('telefones_json')
        if telefones_json:
            try:
                telefones = json.loads(telefones_json)
                for numero in telefones:
                    if numero:
                        ClienteTelefone.objects.create(
                            cliente=cliente,
                            numero=numero
                        )
            except json.JSONDecodeError:
                messages.warning(request, "Telefones inválidos. Não foi possível salvar.")

        # =========================
        # 4️⃣ Salvar Cônjuge (JSON)
        # =========================
        conjuge_json = request.POST.get('conjuge_json')

        print("CONJUGE_JSON:", request.POST.get("conjuge_json"))

        if conjuge_json:
            try:
                conjuge_data = json.loads(conjuge_json)
                print(conjuge_data)

                form_conjuge = ClienteConjugeForm(conjuge_data)
                print(form_conjuge)

                if form_conjuge.is_valid():
                    conjuge = form_conjuge.save(commit=False)
                    conjuge.cliente = cliente
                    conjuge.is_ativo = True
                    conjuge.save()
                else:
                    messages.warning(
                        request,
                        f"Cônjuge não salvo: {form_conjuge.errors.as_text()}"
                    )

            except json.JSONDecodeError:
                messages.warning(request, "Cônjuge não salvo: JSON inválido")

        print("CONJUGE_JSON:", conjuge_json)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(conjuge_json)

        # =========================
        # Finalização
        # =========================
        messages.success(request, "Cliente cadastrado com sucesso!")

        if lote_id:
            return redirect(f'/vendas/insert_reserva/{lote_id}/')
        if veio_da_lista:
            return redirect('lista-cliente')

        return redirect('lista-cliente')

    # =========================
    # GET
    # =========================
    form = ClienteForm()
    formConjuge = ClienteConjugeForm()
    formEndereco = ClienteEnderecoForm()
    formTelefone = ClienteTelefoneForm()

    context = {
        'form': form,
        'formConjuge': formConjuge,
        'formEndereco': formEndereco,
        'formTelefone': formTelefone,
        'veio_da_lista': veio_da_lista,
        'lote_id': lote_id,
    }

    return render(request, 'cliente.html', context)



@has_permission_decorator('alterarCliente')
def atualizarCliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    # Pode não existir
    conjuge = ClienteConjuge.objects.filter(cliente=cliente).first()

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)

        if not form.is_valid():
            messages.error(request, "Verifique os campos obrigatórios.")
            return render(request, 'cliente_update.html', {
                'form': form,
                'cliente': cliente
            })

        # =========================
        # 1️⃣ Atualiza Cliente
        # =========================
        cliente = form.save()

        # =========================
        # 2️⃣ ENDEREÇO (JSON)
        # =========================
        endereco_json = request.POST.get('endereco_json')
        if endereco_json:
            endereco_data = json.loads(endereco_json)

            endereco, created = ClienteEndereco.objects.get_or_create(
                cliente=cliente
            )

            for campo, valor in endereco_data.items():
                setattr(endereco, campo, valor)

            endereco.is_ativo = True
            endereco.save()

        # =========================
        # 3️⃣ TELEFONES (JSON)
        # =========================
        telefones_json = request.POST.get('telefones_json')
        if telefones_json:
            ClienteTelefone.objects.filter(cliente=cliente).delete()

            telefones = json.loads(telefones_json)
            for tel in telefones:
                ClienteTelefone.objects.create(
                    cliente=cliente,
                    numero=tel
                )

        # =========================
        # 4️⃣ CÔNJUGE (REGRA DE NEGÓCIO)
        # =========================
        if cliente.estado_civil != 'CASADO':
            ClienteConjuge.objects.filter(cliente=cliente).delete()
        else:
            conjuge_json = request.POST.get('conjuge_json')
            if conjuge_json:
                conjuge_data = json.loads(conjuge_json)

                if conjuge:
                    for campo, valor in conjuge_data.items():
                        setattr(conjuge, campo, valor)
                else:
                    conjuge = ClienteConjuge(cliente=cliente, **conjuge_data)

                conjuge.is_ativo = True
                conjuge.save()

        messages.success(request, "Cliente atualizado com sucesso!")
        return redirect('lista-cliente')

    # =========================
    # GET
    # =========================

    form = ClienteForm(instance=cliente)
    formConjuge = ClienteConjugeForm(instance=cliente)
    formEndereco = ClienteEnderecoForm(instance=cliente)
    formTelefone = ClienteTelefoneForm(instance=cliente)

    context = {
        'form': form,
        'cliente': cliente,
        'formConjuge': formConjuge,
        'formEndereco': formEndereco,
        'formTelefone': formTelefone
    }

    return render(request, 'cliente_update.html', context)




## Relatório

@has_permission_decorator('relatorioCliente')
def listaCliente(request):
    # pré-carrega telefones para evitar consultas repetidas
    clientes_qs = Cliente.objects.filter(
        is_ativo=True
    ).prefetch_related(
        Prefetch(
            'telefones',
            queryset=ClienteTelefone.objects.filter(is_ativo=True),
            to_attr='telefones_list'
        )
    ).order_by('name')

    get_client = request.GET.get('client')

    if get_client:
        clientes_qs = clientes_qs.filter(
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(email__icontains=get_client)
        )

    paginator = Paginator(clientes_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_cliente.html', {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,
    })


"""def listaCliente(request):
    clientes = Cliente.objects.filter(is_ativo=True).order_by('name')

    get_client = request.GET.get('client')

    if get_client:
        clientes = clientes.filter(  # mantém filtro original e ordenação
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(fone__icontains=get_client) |
            Q(email__icontains=get_client)
        )

    paginator = Paginator(clientes, 10)  # 10 clientes por página (ajuste conforme quiser)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,  # só os da página atual
    }

    return render(request, 'lista_cliente.html', context)"""


@has_permission_decorator('relatorioClienteRelatorio')
def listaClienteRelatorio(request):
    clientes = Cliente.objects.filter(is_ativo=True).order_by('name')

    get_client = request.GET.get('client')

    if get_client:  ## Filtra por nome, documento ou email do cliente
        clientes = Cliente.objects.filter(
            # Q(is_ativo__icontains='False') |
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(fone__icontains=get_client) |
            Q(email__icontains=get_client))

    paginator = Paginator(clientes, 10)  # 10 clientes por página (ajuste conforme quiser)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,  # só os da página atual
    }
    return render(request, 'lista_cliente_relatorio.html', context)


@has_permission_decorator('deletarCliente')
def deleteCliente(request, id):
    cliente = Cliente.objects.get(id=id)
    cliente.is_ativo = False
    cliente.save()
    return redirect('lista-cliente')
