import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.forms import modelformset_factory
from rolepermissions.decorators import has_permission_decorator

from .forms import ClienteForm, ClienteUpdateForm, ClienteConjugeForm, ClienteEnderecoForm, ClienteTelefoneForm
from .models import Cliente, ClienteConjuge, ClienteEndereco, ClienteTelefone



@has_permission_decorator('selectCliente')
def selectCliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    data = {
        "id": cliente.id,
        "name": cliente.name,
        "documento": cliente.documento,
        "email": cliente.email,
    }

    return JsonResponse(data)



@has_permission_decorator('criarCliente')
def criarCliente(request):
    lote_uuid = request.GET.get('lote_uuid') or request.POST.get('lote_uuid')
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
                'lote_uuid': lote_uuid,
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

        if lote_uuid:
            return redirect(f'/vendas/insert_reserva/{lote_uuid}/')
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
        'lote_uuid': lote_uuid,
    }

    return render(request, 'cliente.html', context)


@has_permission_decorator('alterarCliente')
def atualizarCliente(request, cliente_uuid):
    # =========================
    # BUSCA CLIENTE E RELACIONADOS
    # =========================
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
    conjuge = ClienteConjuge.objects.filter(cliente=cliente).first()
    endereco = ClienteEndereco.objects.filter(cliente=cliente).first() #getattr(cliente.id, 'endereco', None)

    previous = request.META.get('HTTP_REFERER', '')
    veio_da_lista = '/clientes/listar_clientes/' in previous

    # =========================
    # GET
    # =========================
    if request.method == 'GET':
        form = ClienteUpdateForm(instance=cliente)
        formConjuge = ClienteConjugeForm(instance=conjuge)
        formEndereco = ClienteEnderecoForm(instance=endereco)

        telefones = list(
            ClienteTelefone.objects
            .filter(cliente=cliente)
            .values_list('numero', flat=True)
        )

        context = {
            'form': form,
            'cliente': cliente,
            'formConjuge': formConjuge,
            'formEndereco': formEndereco,
            'telefones_json': json.dumps(telefones),
            'veio_da_lista': veio_da_lista
        }

        return render(request, 'cliente_update.html', context)

    # =========================
    # POST
    # =========================
    form = ClienteUpdateForm(request.POST, instance=cliente)

    if not form.is_valid():
        messages.error(request, "Verifique os campos obrigatórios.")

        context = {
            'form': form,
            'cliente': cliente,
            'formConjuge': ClienteConjugeForm(instance=conjuge),
            'formEndereco': ClienteEnderecoForm(instance=endereco),
            'telefones_json': request.POST.get('telefones_json', '[]'),
            'veio_da_lista': veio_da_lista
        }

        return render(request, 'cliente_update.html', context)

    # =========================
    # 1️⃣ CLIENTE
    # =========================
    cliente = form.save()

    # =========================
    # 2️⃣ ENDEREÇO
    # =========================
    endereco_json = request.POST.get('endereco_json')
    if endereco_json:
        endereco_data = json.loads(endereco_json)
        endereco, _ = ClienteEndereco.objects.get_or_create(cliente=cliente)

        for campo, valor in endereco_data.items():
            setattr(endereco, campo, valor)

        endereco.is_ativo = True
        endereco.save()

    # =========================
    # 3️⃣ TELEFONES (JSON)
    # =========================
    telefones_json = request.POST.get('telefones_json', '[]')
    telefones_recebidos = json.loads(telefones_json)

    telefones_existentes = list(
        ClienteTelefone.objects.filter(cliente=cliente)
    )

    numeros_existentes = {t.numero for t in telefones_existentes}
    numeros_recebidos = set(telefones_recebidos)

    # ➕ novos
    for numero in numeros_recebidos - numeros_existentes:
        ClienteTelefone.objects.create(
            cliente=cliente,
            numero=numero
        )

    # ➖ removidos
    for telefone in telefones_existentes:
        if telefone.numero not in numeros_recebidos:
            telefone.delete()

    # =========================
    # 4️⃣ CÔNJUGE
    # =========================
    if cliente.estado_civil != 'casado':
        ClienteConjuge.objects.filter(cliente=cliente).delete()
    else:
        conjuge_json = request.POST.get('conjuge_json')
        if conjuge_json:
            conjuge_data = json.loads(conjuge_json)
            conjuge, _ = ClienteConjuge.objects.get_or_create(cliente=cliente)

            for campo, valor in conjuge_data.items():
                setattr(conjuge, campo, valor)

            conjuge.is_ativo = True
            conjuge.save()

    messages.success(request, "Cliente atualizado com sucesso!")
    return redirect('lista-cliente')

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
    cliente_obj = paginator.get_page(page_number)

    return render(request, 'lista_cliente.html', {
        'cliente_obj': cliente_obj,
        'clientes': cliente_obj.object_list,
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
    try:
        cliente = Cliente.objects.get(id=id)

        # Deletar telefones relacionados
        if hasattr(cliente, 'telefones'):
            cliente.telefones.all().delete()

        # Deletar endereços relacionados
        if hasattr(cliente, 'enderecos'):
            cliente.enderecos.all().delete()

        # Deletar cônjuge relacionado
        if hasattr(cliente, 'conjuge') and cliente.conjuge is not None:
            cliente.conjuge.delete()

        # Marcar como inativo
        cliente.is_ativo = False

        # Evitar conflito de UNIQUE no email
        if cliente.email:
            cliente.email = f"deleted_{cliente.id}@example.com"

        # Salvar alterações
        cliente.save()

        return redirect('lista-cliente')

    except Cliente.DoesNotExist:
        messages.error(request, "Cliente não encontrado.")
        return redirect('lista-cliente')

    except Exception as e:
        messages.error(request, f"Erro ao deletar cliente: {str(e)}")
        return redirect('lista-cliente')
