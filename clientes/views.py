import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from rolepermissions.decorators import has_permission_decorator

from .forms import (
    ClienteConjugeForm,
    ClienteEnderecoForm,
    ClienteForm,
    ClienteTelefoneForm,
    ClienteUpdateForm,
)
from .models import Cliente, ClienteTelefone


# ===================================================================
# HELPERS
# ===================================================================

def _load_json_payload(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _normalize_telefones(telefones):
    if not isinstance(telefones, list):
        return []
    return [t for t in telefones if t]


def _endereco_preenchido(cleaned_data):
    required = ('end_cep', 'end_rua', 'end_numero', 'end_bairro', 'end_cidade', 'end_estado')
    return all((cleaned_data.get(f) or '').strip() for f in required)


def _render_cliente_form(request, template, form, cliente=None,
                         form_endereco=None, form_conjuge=None,
                         telefones_json='[]', veio_da_lista=False, lote_uuid=None):
    context = {
        'form': form,
        'formConjuge': form_conjuge or ClienteConjugeForm(instance=cliente),
        'formEndereco': form_endereco or ClienteEnderecoForm(instance=cliente),
        'formTelefone': ClienteTelefoneForm(),
        'telefones_json': telefones_json,
        'veio_da_lista': veio_da_lista,
        'lote_uuid': lote_uuid,
    }
    if cliente is not None:
        context['cliente'] = cliente
    return render(request, template, context)


# ===================================================================
# selectCliente
# ===================================================================

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


# ===================================================================
# selectClienteEndereco — mantido como endpoint de transição
# ===================================================================

# @has_permission_decorator('selectClienteEndereco')
def selectClienteEndereco(request, endereco_id):
    raise Http404


# ===================================================================
# criarCliente
# ===================================================================

@has_permission_decorator('criarCliente')
def criarCliente(request):
    lote_uuid = request.GET.get('lote_uuid') or request.POST.get('lote_uuid')
    previous = request.META.get('HTTP_REFERER', '')
    veio_da_lista = '/clientes/listar_clientes/' in previous

    if request.method == 'POST':
        telefones_json = request.POST.get('telefones_json', '[]')
        form = ClienteForm(request.POST)
        form_endereco = ClienteEnderecoForm(request.POST)
        form_conjuge = ClienteConjugeForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Verifique os campos obrigatórios.")
            return _render_cliente_form(
                request, 'cliente.html', form,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json=telefones_json,
                veio_da_lista=veio_da_lista, lote_uuid=lote_uuid,
            )

        if not form_endereco.is_valid() or not _endereco_preenchido(form_endereco.cleaned_data):
            messages.error(request, "Informe um endereço completo para cadastrar o cliente.")
            return _render_cliente_form(
                request, 'cliente.html', form,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json=telefones_json,
                veio_da_lista=veio_da_lista, lote_uuid=lote_uuid,
            )

        telefones = _normalize_telefones(_load_json_payload(telefones_json, []))
        if not telefones:
            messages.error(request, "Informe pelo menos um telefone para cadastrar o cliente.")
            return _render_cliente_form(
                request, 'cliente.html', form,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json='[]', veio_da_lista=veio_da_lista, lote_uuid=lote_uuid,
            )

        is_casado = form.cleaned_data.get('estado_civil') == 'casado'
        if is_casado:
            if not form_conjuge.is_valid() or not form_conjuge.cleaned_data.get('conj_nome'):
                messages.error(request, "Informe o cônjuge para cadastrar cliente casado.")
                return _render_cliente_form(
                    request, 'cliente.html', form,
                    form_endereco=form_endereco, form_conjuge=form_conjuge,
                    telefones_json=json.dumps(telefones),
                    veio_da_lista=veio_da_lista, lote_uuid=lote_uuid,
                )

        with transaction.atomic():
            cliente = form.save(commit=False)
            for field, value in form_endereco.cleaned_data.items():
                setattr(cliente, field, value)
            if is_casado:
                for field, value in form_conjuge.cleaned_data.items():
                    setattr(cliente, field, value)
            cliente.save()

            for numero in telefones:
                if numero:
                    ClienteTelefone.objects.create(cliente=cliente, numero=numero)

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


# ===================================================================
# atualizarCliente
# ===================================================================

@has_permission_decorator('alterarCliente')
def atualizarCliente(request, cliente_uuid):
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
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
            'formConjuge': ClienteConjugeForm(instance=cliente),
            'formEndereco': ClienteEnderecoForm(instance=cliente),
            'telefones_json': json.dumps(telefones),
            'veio_da_lista': veio_da_lista,
        })

    form = ClienteUpdateForm(request.POST, instance=cliente)
    form_endereco = ClienteEnderecoForm(request.POST, instance=cliente)
    form_conjuge = ClienteConjugeForm(request.POST, instance=cliente)

    if not form.is_valid():
        messages.error(request, "Verifique os campos obrigatórios.")
        return _render_cliente_form(
            request, 'cliente_update.html', form, cliente=cliente,
            form_endereco=form_endereco, form_conjuge=form_conjuge,
            telefones_json=request.POST.get('telefones_json', '[]'),
            veio_da_lista=veio_da_lista,
        )

    if not form_endereco.is_valid() or not _endereco_preenchido(form_endereco.cleaned_data):
        messages.error(request, "O cliente precisa ter um endereço completo.")
        return _render_cliente_form(
            request, 'cliente_update.html', form, cliente=cliente,
            form_endereco=form_endereco, form_conjuge=form_conjuge,
            telefones_json=request.POST.get('telefones_json', '[]'),
            veio_da_lista=veio_da_lista,
        )

    telefones_json = request.POST.get('telefones_json', '[]')
    telefones_recebidos = _normalize_telefones(_load_json_payload(telefones_json, []))
    if not telefones_recebidos:
        messages.error(request, "O cliente precisa ter pelo menos um telefone.")
        return _render_cliente_form(
            request, 'cliente_update.html', form, cliente=cliente,
            form_endereco=form_endereco, form_conjuge=form_conjuge,
            telefones_json='[]', veio_da_lista=veio_da_lista,
        )

    estado_civil_final = form.cleaned_data.get('estado_civil')
    is_casado = estado_civil_final == 'casado'
    if is_casado:
        if not form_conjuge.is_valid() or not form_conjuge.cleaned_data.get('conj_nome'):
            messages.error(request, "Informe o cônjuge para cliente casado.")
            return _render_cliente_form(
                request, 'cliente_update.html', form, cliente=cliente,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json=json.dumps(telefones_recebidos),
                veio_da_lista=veio_da_lista,
            )

    with transaction.atomic():
        cliente_obj = form.save(commit=False)
        for field, value in form_endereco.cleaned_data.items():
            setattr(cliente_obj, field, value)
        if is_casado:
            for field, value in form_conjuge.cleaned_data.items():
                setattr(cliente_obj, field, value)
        else:
            cliente_obj.conj_nome = None
            cliente_obj.conj_numero_rg = None
            cliente_obj.conj_orgao_emissor_rg = None
            cliente_obj.conj_documento = None
        cliente_obj.save()

        telefones_existentes = list(ClienteTelefone.objects.filter(cliente=cliente_obj))
        numeros_existentes = {t.numero for t in telefones_existentes}
        numeros_recebidos = {n for n in telefones_recebidos if n}

        for numero in numeros_recebidos - numeros_existentes:
            ClienteTelefone.objects.create(cliente=cliente_obj, numero=numero)
        for telefone in telefones_existentes:
            if telefone.numero not in numeros_recebidos:
                telefone.delete()

    messages.success(request, "Cliente atualizado com sucesso!")
    return redirect('lista-cliente')


# ===================================================================
# listaCliente
# ===================================================================

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


# ===================================================================
# listaClienteRelatorio
# ===================================================================

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


# ===================================================================
# deleteCliente
# ===================================================================

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