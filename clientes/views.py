from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .forms import ClienteForm, ClienteModalForm
from vendas.forms import RegisterVendaForm

from .models import Cliente
from empreendimentos.models import Lote
from django.db.models import Q
from rolepermissions.decorators import has_role_decorator

from django.contrib.auth.decorators import login_required

from django.db import IntegrityError

@has_role_decorator('selectCliente')
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

@has_role_decorator('criarCliente')
def criarCliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista-cliente')  # Este nome deve bater com "name" no urls.py

    form = ClienteForm()
    return render(request, 'cliente.html', {'form': form})


@has_role_decorator('criarClienteModal')
def criarClienteModal(request):

    if request.method == "POST":
        form = ClienteModalForm(request.POST)  # Usa o formulário para validação

        if form.is_valid():
            form.save()  # Salva um novo cliente
            messages.success(request, "Cliente Cadastrado com sucesso!")
            return redirect('/vendas/insert_reserva/' + request.POST.get('lote_id') + '/')  # Este nome deve bater com "name" no urls.py


    form = ClienteForm()
    return redirect('/vendas/insert_reserva/' + request.POST.get('lote_id') + '/')





@has_role_decorator('alterarCliente')
def alteraCliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == 'GET':
        form = ClienteForm(instance=cliente)  # Preenche o formulário com os dados do cliente
        context = {'form': form, 'cliente': cliente}  # adiciona o cliente no contexto
        return render(request, 'update_cliente.html', context)

    if request.method == 'POST':  # Use POST para formulários HTML
        form = ClienteForm(request.POST, instance=cliente)  # Passa os dados e a instância para o formulário

        if form.is_valid():
            form.save()
            return redirect('lista-cliente')  # Redireciona para a lista de clientes

        context = {'form': form, 'cliente': cliente}  # adiciona o cliente no contexto
        return render(request, 'update_cliente.html', context)  # retorna o form com os erros.

    # Se não for GET nem POST, retorna um erro (ou redireciona, dependendo do caso)
    return redirect('lista-cliente')  # redireciona para a lista de clientes, caso o metodo não seja get nem post

@has_role_decorator('deletarCliente')
def deleteCliente(request, id):
    cliente = Cliente.objects.get(id=id)
    cliente.is_ativo = True
    cliente.save()
    return redirect('lista-cliente')

## Relatório

@has_role_decorator('relatorioCliente')
def listaCliente(request):
    clientes = Cliente.objects.filter(is_ativo=False).order_by('name')

    get_client = request.GET.get('client')

    if get_client:  ## Filtra por nome, documento ou email do cliente
        clientes = Cliente.objects.filter(
            #Q(is_ativo__icontains='False') |
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(fone__icontains=get_client) |
            Q(email__icontains=get_client))

    context = {'clientes': clientes}
    return render(request, 'lista_cliente.html', context)

def listaClienteRelatorio(request):
    clientes = Cliente.objects.filter(is_ativo=False).order_by('name')

    get_client = request.GET.get('client')

    if get_client:  ## Filtra por nome, documento ou email do cliente
        clientes = Cliente.objects.filter(
            #Q(is_ativo__icontains='False') |
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(fone__icontains=get_client) |
            Q(email__icontains=get_client))

    context = {'clientes': clientes}
    return render(request, 'lista_cliente_relatorio.html', context)
