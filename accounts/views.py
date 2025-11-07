from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

from .models import User, UsuarioEmpreendimento
from empreendimentos.models import Empreendimento

from .forms import UserCreationForm, UserChangeForm
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_django
from django.db.models import Q
from django.core.paginator import Paginator
from rolepermissions.decorators import has_permission_decorator


def login(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect(reverse('lista-empreendimento'))
        return render(request, 'login.html')

    elif request.method == 'POST':
        login = request.POST.get('email')
        senha = request.POST.get('senha')

        user = authenticate(username=login, password=senha, is_active=True)

        if not user:
            # TODO: Redirecionar com mensagem de erro
            messages.error(request, "Usuário inválido! Tente novamente.")
            return redirect(reverse('login'))

        login_django(request, user)
        messages.success(request, "Usuário Logado com sucesso.!")
        return redirect(reverse('lista-empreendimento'))


def logout(request):
    request.session.flush()
    return redirect(reverse('login'))


@has_permission_decorator('listarUsuario')
def listarUsuario(request):
    usuarios = User.objects.all().order_by('first_name')

    # Mapeamento dos tipos de usuário
    tipo_usuario_map = {
        'A': 'Administrador',
        'C': 'Corretor',
        'P': 'Proprietário',
    }

    # Filtros vindos da query string
    get_user = request.GET.get('user', '').strip()
    get_tipo_user = request.GET.get('tipo_user', '').strip()
    get_is_active = request.GET.get('is_active', '').strip()

    # Aplicação dos filtros
    if get_user:
        usuarios = usuarios.filter(
            Q(username__icontains=get_user)
            | Q(email__icontains=get_user)
            | Q(contato__icontains=get_user)  # alterei 'phone' → 'contato' (como no seu form)
        )

    if get_tipo_user:
        usuarios = usuarios.filter(tipo_usuario=get_tipo_user)

    if get_is_active:
        # Filtra explicitamente True/False
        if get_is_active.lower() in ['true', '1', 'ativo']:
            usuarios = usuarios.filter(is_active=True)
        elif get_is_active.lower() in ['false', '0', 'inativo']:
            usuarios = usuarios.filter(is_active=False)

    # Adicionando o display legível para tipo_usuario
    for usuario in usuarios:
        usuario.tipo_usuario_display = tipo_usuario_map.get(usuario.tipo_usuario, '—')

    # Paginação
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'usuarios': page_obj.object_list,
        'filtros': {
            'user': get_user,
            'tipo_user': get_tipo_user,
            'is_active': get_is_active,
        }
    }

    return render(request, 'lista_usuarios.html', context)


@has_permission_decorator('criarUsuario')
def criarUsuario(request):
    template_name = 'usuario.html'

    if request.method == 'GET':
        return render(request, template_name)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        contato = request.POST.get('contato')
        creci = request.POST.get('creci')
        tipo_usuario = request.POST.get('tipo_usuario')

        user = User.objects.filter(email=email)

        if user.exists():
            # TODO: Utilizar messages do Django
            return HttpResponse('Email já existe! Tente novamente.')

        user = User.objects.create_user(first_name=first_name, last_name=last_name ,username=email, email=email, password=senha, contato=contato, creci=creci,
                                        tipo_usuario=tipo_usuario)

        messages.success(request, "Usuario criada com sucesso!")
        # TODO: Redirecionar com uma mensagem
        return redirect('lista-usuario')

    context = {
        'form': form
    }
    return render(request, template_name, context)


@has_permission_decorator('alterarUsuario')
def alteraUsuario(request, id):
    usuario = get_object_or_404(User, id=id)
    template_name = 'update_usuario.html'

    if request.method == 'GET':
        form = UserChangeForm(instance=usuario)  # Preenche o formulário com os dados do usuario
        context = {'form': form, 'usuario': usuario}  # adiciona o usuario no contexto
        return render(request, template_name, context)

    if request.method == 'POST':  # Use POST para formulários HTML
        form = UserChangeForm(request.POST, instance=usuario)  # Passa os dados e a instância para o formulário

        if form.is_valid():
            form.save()
            return redirect('lista-usuario')  # Redireciona para a lista de usuarios

        context = {'form': form, 'usuario': usuario}  # adiciona o usuario no contexto
        return render(request, template_name, context)  # retorna o form com os erros.

    # Se não for GET nem POST, retorna um erro (ou redireciona, dependendo do caso)
    return redirect('lista-cliente')  # redireciona para a lista de usuarios, caso o metodo não seja get nem post


@has_permission_decorator('deletarUsuario')
def deleteUsuario(request, id):
    usuario = User.objects.get(id=id)
    usuario.is_active = False
    usuario.save()
    return redirect('lista-usuario')

@has_permission_decorator('criarUsuarioEmpreendimento')
def criarUsuariosEmpreendimento(request):
    if request.method == 'POST':
        ids_usuarios = request.POST.getlist('usuarios_selecionados')
        id_empreendimento = request.POST.get('empreendimento')

        empreendimento = get_object_or_404(Empreendimento, id=id_empreendimento)

        for user_id in ids_usuarios:
            usuario = User.objects.get(id=user_id)
            relacao, created = UsuarioEmpreendimento.objects.get_or_create(
                usuario=usuario,
                empreendimento=empreendimento,
                defaults={'ativo': True}
            )

            if not created:
                relacao.ativo = True
                relacao.save()

        messages.success(request, "Usuários associados com sucesso.")
        return redirect('detalhe-empreendimento', id=empreendimento.id)

    return redirect('lista-empreendimento-tabela')


@has_permission_decorator('deleteUsuarioEmpreendimento')
def deleteUsuarioEmpreendimento(request, id):
    usuario = UsuarioEmpreendimento.objects.get(id=id)
    usuario.ativo = False
    usuario.save()
    return redirect('detalhe-empreendimento', id=usuario.empreendimento.id)
