from django.contrib import messages
from django.contrib.auth import authenticate, login as login_django, logout as logout_django, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from rolepermissions.decorators import has_permission_decorator

from empreendimentos.models import Empreendimento
from vendas.models import RegisterVenda

from .apps import ACOES, MODULOS_GLOT
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


def _contexto_vendas_corretor(usuario, request):
    eh_corretor = usuario.groups.filter(name='Corretor').exists()
    if not eh_corretor:
        return {'eh_corretor': False}

    vendas = RegisterVenda.objects.filter(corretor=usuario).select_related(
        'lote', 'lote__quadra', 'lote__quadra__empr', 'cliente'
    ).order_by('-dt_venda', '-id')

    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()
    empreendimento_id = request.GET.get('empreendimento', '').strip()

    if data_inicio:
        vendas = vendas.filter(dt_venda__gte=data_inicio)
    if data_fim:
        vendas = vendas.filter(dt_venda__lte=data_fim)
    if empreendimento_id:
        vendas = vendas.filter(lote__quadra__empr_id=empreendimento_id)

    totais = vendas.aggregate(qtd=Count('id'), valor_total=Sum('valor_financiado'))

    paginator = Paginator(vendas, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    querystring = request.GET.copy()
    querystring.pop('page', None)

    return {
        'eh_corretor': True,
        'vendas': page_obj.object_list,
        'page_obj': page_obj,
        'totais': totais,
        'empreendimentos': Empreendimento.objects.filter(is_ativo=True).order_by('nome'),
        'filtros_venda': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'empreendimento': empreendimento_id,
        },
        'querystring': querystring.urlencode(),
    }


@has_permission_decorator('alterarUsuario')
def alteraUsuario(request, id):
    usuario = get_object_or_404(User, id=id)
    template_name = 'update_usuario.html'

    if request.method == 'GET':
        form = UserChangeForm(instance=usuario)
        context = {'form': form, 'usuario': usuario}
        context.update(_contexto_vendas_corretor(usuario, request))
        return render(request, template_name, context)

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


# =========================================================
# Grupos de acesso (Fase 2)
# =========================================================

GRUPOS_PROTEGIDOS = ['Administrador', 'Corretor', 'Proprietario']


def _is_admin(user):
    return user.is_authenticated and user.tipo_usuario == 'ADMINISTRADOR'


def _matriz_permissoes(codenames_marcados=None):
    marcados = set(codenames_marcados or [])
    matriz = []
    for codigo, nome in MODULOS_GLOT:
        linha = {'codigo': codigo, 'nome': nome, 'acoes': []}
        for acao in ACOES:
            codename = f'glot_{codigo}_{acao}'
            linha['acoes'].append({
                'acao': acao,
                'codename': codename,
                'marcado': codename in marcados,
            })
        matriz.append(linha)
    return matriz


def _codenames_validos(request):
    enviados = request.POST.getlist('permissoes[]')
    return [c for c in enviados if c.startswith('glot_')]


@login_required
@user_passes_test(_is_admin)
def lista_grupos(request):
    grupos = Group.objects.annotate(
        num_permissoes=Count('permissions', distinct=True),
        num_usuarios=Count('user', distinct=True),
    ).order_by('name')

    context = {
        'grupos': grupos,
        'grupos_protegidos': GRUPOS_PROTEGIDOS,
    }
    return render(request, 'accounts/lista_grupos.html', context)


@login_required
@user_passes_test(_is_admin)
def criar_grupo(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        codenames = _codenames_validos(request)

        if not nome:
            messages.error(request, "Informe o nome do grupo.")
        elif Group.objects.filter(name=nome).exists():
            messages.error(request, "Ja existe um grupo com esse nome.")
        else:
            grupo = Group.objects.create(name=nome)
            grupo.permissions.set(Permission.objects.filter(codename__in=codenames))
            messages.success(request, f"Grupo '{nome}' criado com sucesso.")
            return redirect('lista_grupos')

        return render(request, 'accounts/form_grupo.html', {
            'titulo': 'Novo Grupo',
            'nome': nome,
            'acoes': ACOES,
            'matriz': _matriz_permissoes(codenames),
        })

    return render(request, 'accounts/form_grupo.html', {
        'titulo': 'Novo Grupo',
        'nome': '',
        'acoes': ACOES,
        'matriz': _matriz_permissoes(),
    })


@login_required
@user_passes_test(_is_admin)
def editar_grupo(request, pk):
    grupo = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        codenames = _codenames_validos(request)

        if not nome:
            messages.error(request, "Informe o nome do grupo.")
        elif Group.objects.filter(name=nome).exclude(pk=grupo.pk).exists():
            messages.error(request, "Ja existe outro grupo com esse nome.")
        else:
            if grupo.name not in GRUPOS_PROTEGIDOS:
                grupo.name = nome
                grupo.save(update_fields=['name'])
            grupo.permissions.set(Permission.objects.filter(codename__in=codenames))
            messages.success(request, f"Grupo '{grupo.name}' atualizado com sucesso.")
            return redirect('lista_grupos')

        return render(request, 'accounts/form_grupo.html', {
            'titulo': f'Editar Grupo: {grupo.name}',
            'nome': nome,
            'acoes': ACOES,
            'matriz': _matriz_permissoes(codenames),
            'grupo': grupo,
            'protegido': grupo.name in GRUPOS_PROTEGIDOS,
        })

    marcados = grupo.permissions.values_list('codename', flat=True)
    return render(request, 'accounts/form_grupo.html', {
        'titulo': f'Editar Grupo: {grupo.name}',
        'nome': grupo.name,
        'acoes': ACOES,
        'matriz': _matriz_permissoes(marcados),
        'grupo': grupo,
        'protegido': grupo.name in GRUPOS_PROTEGIDOS,
    })


@login_required
@user_passes_test(_is_admin)
@require_POST
def excluir_grupo(request, pk):
    grupo = get_object_or_404(Group, pk=pk)

    if grupo.name in GRUPOS_PROTEGIDOS:
        messages.error(request, "Grupos padrao do sistema nao podem ser excluidos.")
        return redirect('lista_grupos')

    if grupo.user_set.exists():
        messages.error(request, "Grupo possui usuarios vinculados e nao pode ser excluido.")
        return redirect('lista_grupos')

    nome = grupo.name
    grupo.delete()
    messages.success(request, f"Grupo '{nome}' excluido com sucesso.")
    return redirect('lista_grupos')


@login_required
@user_passes_test(_is_admin)
def associar_grupos(request, pk):
    usuario = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        grupo_ids = request.POST.getlist('grupos')
        grupos = Group.objects.filter(id__in=grupo_ids)
        usuario.groups.set(grupos)
        nome = usuario.get_full_name().strip() or usuario.username
        messages.success(request, f"Grupos de {nome} atualizados.")
        return redirect('update-usuario', id=usuario.pk)

    atuais = set(usuario.groups.values_list('id', flat=True))
    grupos = Group.objects.annotate(
        num_usuarios=Count('user', distinct=True)
    ).order_by('name')

    grupos_ctx = []
    for g in grupos:
        outros = g.num_usuarios - (1 if g.id in atuais else 0)
        grupos_ctx.append({
            'id': g.id,
            'name': g.name,
            'outros': outros,
            'marcado': g.id in atuais,
        })

    return render(request, 'accounts/associar_grupos.html', {
        'usuario': usuario,
        'grupos': grupos_ctx,
    })


# =========================================================
# Impersonate — acessar como outro usuario (Fase 3)
# =========================================================

@login_required
def impersonate_start(request, pk):
    # Apenas Administrador pode impersonate
    if not _is_admin(request.user):
        messages.error(request, "Sem permissao para acessar como outro usuario.")
        return redirect('lista-usuario')

    # Nao permitir impersonate de si mesmo
    if request.user.pk == pk:
        messages.warning(request, "Voce nao pode acessar como voce mesmo.")
        return redirect('update-usuario', id=pk)

    target = get_object_or_404(User, pk=pk)

    # IMPORTANTE: salvar o id original ANTES do login.
    # login() faz flush da sessao quando o pk do usuario muda,
    # entao gravamos impersonator_id DEPOIS do login.
    original_id = request.user.id
    login_django(request, target, backend='django.contrib.auth.backends.ModelBackend')
    request.session['impersonator_id'] = original_id

    nome = target.get_full_name().strip() or target.username
    messages.info(request, f"Voce esta acessando como {nome}.")
    return redirect('lista-empreendimento')


@login_required
def impersonate_stop(request):
    impersonator_id = request.session.get('impersonator_id')
    if not impersonator_id:
        return redirect('lista-empreendimento')

    original = get_object_or_404(User, pk=impersonator_id)
    # login() faz flush da sessao (pk muda), removendo impersonator_id automaticamente
    login_django(request, original, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, "Voce voltou a sua conta.")
    return redirect('lista-usuario')
