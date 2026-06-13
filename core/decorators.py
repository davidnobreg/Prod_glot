"""
Proteção de views por permissões GLOT (glot_{modulo}_{acao}).

As permissões glot_* foram criadas na Fase 1 ancoradas no model accounts.User,
portanto o app_label correto e' 'accounts' (NAO 'auth').

Uso FBV:
    @glot_permission_required('vendas', 'ver')
    def lista_vendas(request): ...

Uso CBV:
    class CriarVendaView(GlotPermissionMixin, CreateView):
        glot_modulo = 'vendas'
        glot_acao = 'criar'

Comportamento: usuario sem permissao -> mensagem + redirect('login').
Administrador (grupo 'Administrador'/'administrador' ou superuser) ignora a checagem.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect

# app_label real das permissoes glot_* (ancoradas em accounts.User na Fase 1)
GLOT_APP_LABEL = 'accounts'

GRUPOS_ADMIN = ['Administrador', 'administrador']


def _is_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=GRUPOS_ADMIN).exists()


def glot_perm(modulo, acao):
    """Monta a string de permissao no formato 'accounts.glot_{modulo}_{acao}'."""
    return f'{GLOT_APP_LABEL}.glot_{modulo}_{acao}'


def glot_permission_required(modulo, acao):
    perm = glot_perm(modulo, acao)

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if _is_admin(request.user) or request.user.has_perm(perm):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect('login')
        return wrapper
    return decorator


class GlotPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    glot_modulo = None
    glot_acao = None

    def get_permission_required(self):
        if self.glot_modulo and self.glot_acao:
            return [glot_perm(self.glot_modulo, self.glot_acao)]
        return []

    def has_permission(self):
        if _is_admin(self.request.user):
            return True
        return super().has_permission()

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('login')
        messages.error(self.request, 'Você não tem permissão para acessar esta página.')
        return redirect('login')
