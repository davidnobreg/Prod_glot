import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from rolepermissions.decorators import has_permission_decorator

from .forms import (
    ClienteConjugeForm,
    ClienteEnderecoForm,
    ClienteForm,
    ClienteTelefoneForm,
    ClienteUpdateForm,
)
from .models import Cliente, ClienteConjuge, ClienteEndereco, ClienteTelefone


def _load_json_payload(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _render_cliente_form(request, template, form, cliente=None, conjuge=None, endereco=None,
                         telefones_json='[]', veio_da_lista=False, lote_uuid=None):
    context = {
        'form': form,
        'formConjuge': ClienteConjugeForm(instance=conjuge),
        'formEndereco': ClienteEnderecoForm(instance=endereco),
        'formTelefone': ClienteTelefoneForm(),
        'telefones_json': telefones_json,
        'veio_da_lista': veio_da_lista,
        'lote_uuid': lote_uuid,
    }
    if cliente is not None:
        context['cliente'] = cliente
    return render(request, template, context)


@has_permission_decorator('selectCliente')
def selectCliente(request, cliente_uuid):
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)

    data = {
        "uuid": str(cliente.uuid),
        "name": cliente.name,
        "documento": cliente.documento,
        "email": cliente.email,
    }

    return JsonResponse(data)


# @has_permission_decorator('selectClienteEndereco')
def selectClienteEndereco(request, endereco_id):
    endereco = get_object_or_404(ClienteEndereco, id=endereco_id)

    data = {
        "idEndereco": endereco.id,
        "rua": endereco.rua,
        "complemento": endereco.complemento,
        "numero": endereco.numero,
        "bairro": endereco.bairro,
        "cep": endereco.cep,
        "cidade": endereco.cidade,
        "estado": endereco.estado,
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
            messages.error(request, "Verifique os campos obrigatorios.")
            return _render_cliente_form(
                request,
                'cliente.html',
                form,
                veio_da_lista=veio_da_lista,
                lote_uuid=lote_uuid,
            )

        endereco_json = request.POST.get("endereco_json")
        endereco_data = _load_json_payload(endereco_json, {})
        if endereco_json and not isinstance(endereco_data, dict):
            endereco_data = {}
            messages.warning(request, "Endereco invalido. Nao foi possivel salvar.")

        telefones_json = request.POST.get('telefones_json')
        telefones = _load_json_payload(telefones_json, [])
        if telefones_json and not isinstance(telefones, list):
            telefones = []
            messages.warning(request, "Telefones invalidos. Nao foi possivel salvar.")

        conjuge_json = request.POST.get('conjuge_json')
        conjuge_data = _load_json_payload(conjuge_json, {})
        if conjuge_json and not isinstance(conjuge_data, dict):
            conjuge_data = {}
            messages.warning(request, "Conjuge nao salvo: JSON invalido.")

        with transaction.atomic():
            cliente = form.save()

            if endereco_data and any(endereco_data.values()):
                ClienteEndereco.objects.create(
                    cliente=cliente,
                    cep=endereco_data.get('cep', ''),
                    rua=endereco_data.get('rua', ''),
                    numero=endereco_data.get('numero', ''),
                    complemento=endereco_data.get('complemento', ''),
                    bairro=endereco_data.get('bairro', ''),
                    cidade=endereco_data.get('cidade', ''),
                    estado=endereco_data.get('estado', ''),
                    is_ativo=True,
                )

            for numero in telefones:
                if numero:
                    ClienteTelefone.objects.create(
                        cliente=cliente,
                        numero=numero,
                    )

            if conjuge_data and any(conjuge_data.values()):
                form_conjuge = ClienteConjugeForm(conjuge_data)
                if form_conjuge.is_valid():
                    conjuge = form_conjuge.save(commit=False)
                    conjuge.cliente = cliente
                    conjuge.is_ativo = True
                    conjuge.save()
                else:
                    messages.warning(
                        request,
                        f"Conjuge nao salvo: {form_conjuge.errors.as_text()}",
                    )

        messages.success(request, "Cliente cadastrado com sucesso!")

        if lote_uuid:
            return redirect(f'/vendas/insert_reserva/{lote_uuid}/')

        return redirect('lista-cliente')

    context = {
        'form': ClienteForm(),
        'formConjuge': ClienteConjugeForm(),
        'formEndereco': ClienteEnderecoForm(),
        'formTelefone': ClienteTelefoneForm(),
        'veio_da_lista': veio_da_lista,
        'lote_uuid': lote_uuid,
    }

    return render(request, 'cliente.html', context)


@has_permission_decorator('alterarCliente')
def atualizarCliente(request, cliente_uuid):
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
    conjuge = ClienteConjuge.objects.filter(cliente=cliente).first()
    endereco = ClienteEndereco.objects.filter(cliente=cliente).first()

    previous = request.META.get('HTTP_REFERER', '')
    veio_da_lista = '/clientes/listar_clientes/' in previous

    if request.method == 'GET':
        telefones = list(
            ClienteTelefone.objects
            .filter(cliente=cliente)
            .values_list('numero', flat=True)
        )

        return render(request, 'cliente_update.html', {
            'form': ClienteUpdateForm(instance=cliente),
            'cliente': cliente,
            'formConjuge': ClienteConjugeForm(instance=conjuge),
            'formEndereco': ClienteEnderecoForm(instance=endereco),
            'telefones_json': json.dumps(telefones),
            'veio_da_lista': veio_da_lista,
        })

    form = ClienteUpdateForm(request.POST, instance=cliente)

    if not form.is_valid():
        messages.error(request, "Verifique os campos obrigatorios.")
        return _render_cliente_form(
            request,
            'cliente_update.html',
            form,
            cliente=cliente,
            conjuge=conjuge,
            endereco=endereco,
            telefones_json=request.POST.get('telefones_json', '[]'),
            veio_da_lista=veio_da_lista,
        )

    endereco_json = request.POST.get('endereco_json')
    endereco_data = _load_json_payload(endereco_json, {})
    if endereco_json and not isinstance(endereco_data, dict):
        messages.error(request, "Endereco invalido.")
        return _render_cliente_form(
            request,
            'cliente_update.html',
            form,
            cliente=cliente,
            conjuge=conjuge,
            endereco=endereco,
            telefones_json=request.POST.get('telefones_json', '[]'),
            veio_da_lista=veio_da_lista,
        )

    telefones_json = request.POST.get('telefones_json', '[]')
    telefones_recebidos = _load_json_payload(telefones_json, [])
    if not isinstance(telefones_recebidos, list):
        messages.error(request, "Telefones invalidos.")
        return _render_cliente_form(
            request,
            'cliente_update.html',
            form,
            cliente=cliente,
            conjuge=conjuge,
            endereco=endereco,
            telefones_json='[]',
            veio_da_lista=veio_da_lista,
        )

    conjuge_json = request.POST.get('conjuge_json')
    conjuge_data = _load_json_payload(conjuge_json, {})
    if conjuge_json and not isinstance(conjuge_data, dict):
        messages.error(request, "Conjuge invalido.")
        return _render_cliente_form(
            request,
            'cliente_update.html',
            form,
            cliente=cliente,
            conjuge=conjuge,
            endereco=endereco,
            telefones_json=telefones_json,
            veio_da_lista=veio_da_lista,
        )

    with transaction.atomic():
        cliente = form.save()

        if endereco_data and any(endereco_data.values()):
            endereco, _ = ClienteEndereco.objects.get_or_create(cliente=cliente)
            for campo, valor in endereco_data.items():
                if hasattr(endereco, campo):
                    setattr(endereco, campo, valor)
            endereco.is_ativo = True
            endereco.save()

        telefones_existentes = list(ClienteTelefone.objects.filter(cliente=cliente))
        numeros_existentes = {t.numero for t in telefones_existentes}
        numeros_recebidos = {numero for numero in telefones_recebidos if numero}

        for numero in numeros_recebidos - numeros_existentes:
            ClienteTelefone.objects.create(cliente=cliente, numero=numero)

        for telefone in telefones_existentes:
            if telefone.numero not in numeros_recebidos:
                telefone.delete()

        if cliente.estado_civil != 'casado':
            ClienteConjuge.objects.filter(cliente=cliente).delete()
        elif conjuge_data and any(conjuge_data.values()):
            conjuge = ClienteConjuge.objects.filter(cliente=cliente).first()
            form_conjuge = ClienteConjugeForm(conjuge_data, instance=conjuge)
            if form_conjuge.is_valid():
                conjuge = form_conjuge.save(commit=False)
                conjuge.cliente = cliente
                conjuge.is_ativo = True
                conjuge.save()
            else:
                messages.warning(
                    request,
                    f"Conjuge nao salvo: {form_conjuge.errors.as_text()}",
                )

    messages.success(request, "Cliente atualizado com sucesso!")
    return redirect('lista-cliente')


@has_permission_decorator('relatorioCliente')
def listaCliente(request):
    clientes_qs = Cliente.objects.filter(
        is_ativo=True
    ).prefetch_related(
        Prefetch(
            'telefones',
            queryset=ClienteTelefone.objects.filter(is_ativo=True),
            to_attr='telefones_list',
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


@has_permission_decorator('relatorioClienteRelatorio')
def listaClienteRelatorio(request):
    clientes_qs = Cliente.objects.filter(is_ativo=True).prefetch_related(
        Prefetch(
            'telefones',
            queryset=ClienteTelefone.objects.filter(is_ativo=True),
            to_attr='telefones_list',
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

    return render(request, 'lista_cliente_relatorio.html', {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,
    })


@has_permission_decorator('deletarCliente')
def deleteCliente(request, cliente_uuid):
    try:
        cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
        cliente.is_ativo = False

        if cliente.email:
            cliente.email = f"deleted_{cliente.uuid}@example.com"

        cliente.save()

        messages.success(request, "Cliente desativado com sucesso.")
        return redirect('lista-cliente')

    except Exception as e:
        messages.error(request, f"Erro ao desativar cliente: {str(e)}")
        return redirect('lista-cliente')
