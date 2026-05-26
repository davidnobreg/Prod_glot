from django.contrib import messages
from django.contrib.auth import authenticate, login as login_django, logout as logout_django, update_session_auth_hash
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from rolepermissions.decorators import has_permission_decorator

from empreendimentos.models import Empreendimento

from .forms import UserChangeForm, UserCreationForm
from .models import User, UsuarioEmpreendimento


def login(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect(reverse('lista-empreendimento'))
        return render(request, 'login.html')

    email = request.POST.get('email', '').strip().lower()
    senha = request.POST.get('senha')

    user = authenticate(request, username=email, password=senha)

    if not user:
        messages.error(request, "Usuario invalido! Tente novamente.")
        return redirect(reverse('login'))

    login_django(request, user)
    messages.success(request, "Usuario logado com sucesso.")
    return redirect(reverse('lista-empreendimento'))


def logout(request):
    logout_django(request)
    return redirect(reverse('login'))


@has_permission_decorator('listarUsuario')
def listarUsuario(request):
    usuarios = User.objects.all().order_by('first_name')

    get_user = request.GET.get('user', '').strip()
    get_tipo_user = request.GET.get('tipo_user', '').strip()
    get_is_active = request.GET.get('is_active', '').strip()

    if get_user:
        usuarios = usuarios.filter(
            Q(username__icontains=get_user)
            | Q(first_name__icontains=get_user)
            | Q(last_name__icontains=get_user)
            | Q(email__icontains=get_user)
            | Q(creci__icontains=get_user)
            | Q(contato__icontains=get_user)
        )

    if get_tipo_user:
        usuarios = usuarios.filter(tipo_usuario=get_tipo_user)

    if get_is_active:
        if get_is_active.lower() in ['true', '1', 'ativo']:
            usuarios = usuarios.filter(is_active=True)
        elif get_is_active.lower() in ['false', '0', 'inativo']:
            usuarios = usuarios.filter(is_active=False)

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
        },
        'tipo_usuario_choices': User.choices_tipo_usuario,
    }

    return render(request, 'lista_usuarios.html', context)


@has_permission_decorator('criarUsuario')
def criarUsuario(request):
    template_name = 'usuario.html'

    if request.method == 'GET':
        return render(request, template_name, {'form': UserCreationForm()})

    form = UserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Usuario criado com sucesso!")
        return redirect('lista-usuario')

    messages.error(request, "Verifique os dados do usuario.")
    return render(request, template_name, {'form': form})


@has_permission_decorator('alterarUsuario')
def alteraUsuario(request, id):
    usuario = get_object_or_404(User, id=id)
    template_name = 'update_usuario.html'

    if request.method == 'GET':
        form = UserChangeForm(instance=usuario)
        return render(request, template_name, {'form': form, 'usuario': usuario})

    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=usuario)

        if form.is_valid():
            form.save()
            if form.cleaned_data.get('nova_senha1') and request.user.pk == usuario.pk:
                update_session_auth_hash(request, usuario)
            messages.success(request, "Usuario atualizado com sucesso!")
            return redirect('lista-usuario')

        messages.error(request, "Verifique os dados do usuario.")
        return render(request, template_name, {'form': form, 'usuario': usuario})

    return redirect('lista-usuario')


@has_permission_decorator('deletarUsuario')
@require_POST
def deleteUsuario(request, id):
    usuario = get_object_or_404(User, id=id)
    usuario.is_active = False
    usuario.save(update_fields=['is_active'])
    messages.success(request, "Usuario desativado com sucesso.")
    return redirect('lista-usuario')


@has_permission_decorator('criarUsuarioEmpreendimento')
def criarUsuariosEmpreendimento(request):
    if request.method != 'POST':
        return redirect('lista-empreendimento-tabela')

    ids_usuarios = request.POST.getlist('usuarios_selecionados')
    id_empreendimento = request.POST.get('empreendimento')

    empreendimento = get_object_or_404(Empreendimento, id=id_empreendimento)

    for user_id in ids_usuarios:
        usuario = get_object_or_404(User, id=user_id, is_active=True)
        relacao, created = UsuarioEmpreendimento.objects.get_or_create(
            usuario=usuario,
            empreendimento=empreendimento,
            defaults={'ativo': True},
        )

        if not created:
            relacao.ativo = True
            relacao.save(update_fields=['ativo'])

    messages.success(request, "Usuarios associados com sucesso.")
    return redirect('detalhe-empreendimento', id=empreendimento.id)


@has_permission_decorator('deleteUsuarioEmpreendimento')
@require_POST
def deleteUsuarioEmpreendimento(request, id):
    usuario = get_object_or_404(UsuarioEmpreendimento, id=id)
    usuario.ativo = False
    usuario.save(update_fields=['ativo'])
    return redirect('detalhe-empreendimento', id=usuario.empreendimento.id)
