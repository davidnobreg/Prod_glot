from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from ..models import Empreendimento, RepresentanteLegal
from .. import services as empreendimento_services
from accounts.models import User, UsuarioEmpreendimento
from .cadastro import _wizard_get_draft


@has_permission_decorator('selectEmpreendimento')
def selectEmpreendimento(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)

    data = {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
    }

    return JsonResponse(data)


@has_permission_decorator('criarEmpreendimento')
@require_POST
def wizard_representante_del(request, representante_uuid):
    """Remove (soft-delete) representante do rascunho atual. Retorna JSON."""
    draft = _wizard_get_draft(request)
    if draft is None:
        return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado.'}, status=404)

    representante = get_object_or_404(RepresentanteLegal, uuid=representante_uuid, empreendimento=draft)
    if draft.is_ativo:
        empreendimento_services.desativar_representante(representante)
    else:
        representante.delete()
    return JsonResponse({'ok': True})


@require_POST
def criarUsuarioEmpreendimento(request):
    empreendimento_id = request.POST.get('empreendimento')
    users_ids = request.POST.getlist('users')

    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    if not users_ids:
        messages.warning(request, 'Selecione pelo menos um corretor para adicionar.')
        return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)

    usuarios = User.objects.filter(id__in=users_ids)

    adicionados = 0
    reativados = 0

    for usuario in usuarios:
        vinculo, created = UsuarioEmpreendimento.objects.get_or_create(
            empreendimento=empreendimento,
            usuario=usuario,
            defaults={'ativo': True}
        )

        if created:
            adicionados += 1

        elif not vinculo.ativo:
            vinculo.ativo = True
            vinculo.save(update_fields=['ativo'])
            reativados += 1

    if adicionados or reativados:
        messages.success(request, 'Corretor(es) vinculado(s) com sucesso.')
    else:
        messages.info(request, 'Os corretores selecionados já estavam vinculados.')

    return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)


@has_permission_decorator('deleteUsuarioEmpreendimento')
@require_POST
def deleteUsuarioEmpreendimento(request, usuario_empreendimento_uuid):
    vinculo = get_object_or_404(UsuarioEmpreendimento, uuid=usuario_empreendimento_uuid)

    empreendimento_uuid = vinculo.empreendimento.uuid

    vinculo.ativo = False
    vinculo.save(update_fields=['ativo'])

    messages.success(request, 'Corretor removido com sucesso.')

    return redirect('detalhe-empreendimento', uuid=empreendimento_uuid)
