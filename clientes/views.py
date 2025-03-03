from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .forms import ClienteForm
from .models import Cliente


def lista_cliente(request):
    clientes = Cliente.objects.filter(is_ativo=False)
    context = {'clientes': clientes}
    return render(request, 'lista_cliente.html', context)


def select_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    data = {
        "id": cliente.id,
        "name": cliente.name,
        "email": cliente.email,
    }

    return JsonResponse(data)


def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista-cliente')  # Este nome deve bater com "name" no urls.py

    form = ClienteForm()
    return render(request, 'cliente.html', {'form': form})


def criar_cliente_modal(request):
    if request.method == 'POST':

        rid = request.GET.get('rid')

        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/vendas/insert_reserva/' + rid + '/')  # Este nome deve bater com "name" no urls.py

    form = ClienteForm()
    return redirect('/vendas/insert_reserva/' + rid + '/')


def altera_cliente(request, cliente_id):
    cliente = Cliente.objects.get(id=cliente_id)

    print(cliente)

    if request.method == 'GET':
        form = ClienteForm(cliente.GET.get(cliente_id))
        print(form)
        context = {'form': form}
        return render(request, 'update_cliente.html', context)

    if request.method == 'PUT':
        form = ClienteForm(request.POST.get)
        print(form)
        if form.is_valid():
            form.save()
            return redirect('lista-cliente')  # Este nome deve bater com "name" no urls.py

    form = ClienteForm()
    return render(request, 'cliente.html', {'form': form})

    cliente = get_object_or_404(Cliente, id=cliente_id)

    print(cliente)

    name = request.POST.get('name')
    email = request.POST.get('email')
    phone = request.POST.get('phone')

    cliente.name = name
    clientes_cliente = email
    clientes_cliente = phone
    print(clientes_cliente)

    return render(request, 'update_cliente.html')


def delete_cliente(request, id):
    cliente = Cliente.objects.get(id=id)
    cliente.is_ativo = True
    cliente.save()
    return redirect('lista-cliente')
