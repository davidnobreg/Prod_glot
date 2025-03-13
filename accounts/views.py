from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404

from .models import User

from .forms import RegisterForm
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_django
from django.db.models import Q





def listar(request):
    usuarios = User.objects.filter(is_active=True).order_by('username')

    get_user = request.GET.get('user')

    get_tipo_user = request.GET.get('tipo_user')

    if get_user:  ## Filtra por nome, documento ou email do cliente
        usuarios = User.objects.filter(
            Q(is_active__icontains=True) |
            Q(username__icontains=get_user) |
            Q(phone__icontains=get_user) |
            Q(email__icontains=get_user))

    if get_tipo_user:
        usuarios = User.objects.filter(
            Q(is_active__icontains=True) |
            Q(tipo_usuario__icontains=get_tipo_user))

    context = {'usuarios': usuarios}
    return render(request, 'lista_usuarios.html', context)

def criar_usuario(request):
    template_name = 'cadastro.html'
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(
                username=user.username,
                password=form.cleaned_data['password1']
            )
            messages.success(request, "Usuario criada com sucesso!")
            login_django(request, user)

            return redirect('lista-usuario')
            #return HTTPRequest('sucesso')
    else:
        form = RegisterForm()

    context = {
        'form': form
    }
    return render(request, template_name, context)


def altera_usuario(request, id):
    usuario = get_object_or_404(User, id=id)
    template_name = 'update_usuario.html'

    if request.method == 'GET':
        form = RegisterForm(instance=usuario)  # Preenche o formulário com os dados do usuario
        context = {'form': form, 'usuario': usuario}  # adiciona o usuario no contexto
        return render(request, template_name, context)

    if request.method == 'POST':  # Use POST para formulários HTML
        form = RegisterForm(request.POST, instance=usuario)  # Passa os dados e a instância para o formulário

        if form.is_valid():
            form.save()
            return redirect('lista-usuario')  # Redireciona para a lista de usuarios

        context = {'form': form, 'usuario': usuario}  # adiciona o usuario no contexto
        return render(request, template_name, context)  # retorna o form com os erros.

    # Se não for GET nem POST, retorna um erro (ou redireciona, dependendo do caso)
    return redirect('lista-cliente')  # redireciona para a lista de usuarios, caso o metodo não seja get nem post

def delete_usuario(request, id):
    usuario = User.objects.get(id=id)
    usuario.is_active = False
    usuario.save()
    return redirect('lista-usuario')