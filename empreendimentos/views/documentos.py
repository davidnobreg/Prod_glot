from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator
from django.contrib.auth.decorators import login_required

from documentos.models import ModeloDocumento, EmpreendimentoDocumento

from ..forms import DocumentoRepresentanteForm, DocumentoEmpreendimentoForm
from ..models import Empreendimento, RepresentanteLegal, DocumentoRepresentante, DocumentoEmpreendimento
from .. import services as empreendimento_services
from .cadastro import _wizard_get_draft


def _documento_json(documento):
    ext = documento.arquivo.name.rsplit('.', 1)[-1].lower() if '.' in documento.arquivo.name else ''
    return {
        'uuid': str(documento.uuid),
        'nome_exibicao': documento.nome_exibicao(),
        'categoria': documento.categoria,
        'categoria_display': documento.get_categoria_display(),
        'url': documento.arquivo.url,
        'ext': ext,
    }


@has_permission_decorator('criarEmpreendimento')
@require_POST
def wizard_rep_doc_upload(request, rep_uuid):
    """Upload AJAX de documento do representante (ou do cônjuge, se casado)."""
    draft = _wizard_get_draft(request)
    if draft is None:
        return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado.'}, status=404)

    representante = get_object_or_404(RepresentanteLegal, uuid=rep_uuid, empreendimento=draft)

    form = DocumentoRepresentanteForm(request.POST, request.FILES)
    if not form.is_valid():
        erros = '; '.join(f'{campo}: {", ".join(msgs)}' for campo, msgs in form.errors.items())
        return JsonResponse({'ok': False, 'error': erros}, status=400)

    try:
        documento = empreendimento_services.criar_documento_representante(
            representante,
            form.cleaned_data['categoria'],
            form.cleaned_data['arquivo'],
            nome=form.cleaned_data.get('nome', ''),
            usuario=request.user,
        )
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': '; '.join(e.messages)}, status=400)

    return JsonResponse({'ok': True, 'documento': _documento_json(documento)})


@has_permission_decorator('criarEmpreendimento')
@require_POST
def wizard_rep_doc_remover(request, doc_uuid):
    draft = _wizard_get_draft(request)
    if draft is None:
        return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado.'}, status=404)

    documento = get_object_or_404(DocumentoRepresentante, uuid=doc_uuid, representante__empreendimento=draft)
    empreendimento_services.remover_documento_representante(documento)
    return JsonResponse({'ok': True})


@has_permission_decorator('criarEmpreendimento')
@require_POST
def wizard_doc_empreendimento_upload(request):
    """Upload AJAX de documento real (PDF/imagem) vinculado ao empreendimento."""
    draft = _wizard_get_draft(request)
    if draft is None:
        return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado.'}, status=404)

    form = DocumentoEmpreendimentoForm(request.POST, request.FILES)
    if not form.is_valid():
        erros = '; '.join(f'{campo}: {", ".join(msgs)}' for campo, msgs in form.errors.items())
        return JsonResponse({'ok': False, 'error': erros}, status=400)

    documento = empreendimento_services.criar_documento_empreendimento(
        draft,
        form.cleaned_data['categoria'],
        form.cleaned_data['arquivo'],
        nome=form.cleaned_data.get('nome', ''),
        usuario=request.user,
    )

    return JsonResponse({'ok': True, 'documento': _documento_json(documento)})


@has_permission_decorator('criarEmpreendimento')
@require_POST
def wizard_doc_empreendimento_remover(request, doc_uuid):
    draft = _wizard_get_draft(request)
    if draft is None:
        return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado.'}, status=404)

    documento = get_object_or_404(DocumentoEmpreendimento, uuid=doc_uuid, empreendimento=draft)
    empreendimento_services.remover_documento_empreendimento(documento)
    return JsonResponse({'ok': True})


@require_POST
@login_required
def modelo_vincular(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    modelo_id = request.POST.get('modelo_id')
    padrao = request.POST.get('padrao') == '1'

    modelo = get_object_or_404(ModeloDocumento, pk=modelo_id)

    try:
        vinculo, created = EmpreendimentoDocumento.objects.get_or_create(
            empreendimento=empreendimento,
            modelo=modelo,
            defaults={'padrao': padrao, 'ativo': True},
        )
        if not created:
            messages.warning(request, 'Modelo já vinculado.')
        else:
            if padrao:
                # Garante que só um padrão por tipo
                EmpreendimentoDocumento.objects.filter(
                    empreendimento=empreendimento,
                    modelo__tipo=modelo.tipo,
                    padrao=True,
                ).exclude(pk=vinculo.pk).update(padrao=False)
            messages.success(request, f'Modelo "{modelo.titulo}" vinculado.')
    except Exception as e:
        messages.error(request, str(e))

    return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)


@require_POST
@login_required
def modelo_desvincular(request, empreendimento_uuid, vinculo_uuid):
    vinculo = get_object_or_404(EmpreendimentoDocumento, uuid=vinculo_uuid, empreendimento__uuid=empreendimento_uuid)
    empreendimento_uuid = vinculo.empreendimento.uuid
    vinculo.delete()
    messages.success(request, 'Modelo desvinculado.')
    return redirect('detalhe-empreendimento', uuid=empreendimento_uuid)


@require_POST
@login_required
def modelo_set_padrao(request, empreendimento_uuid, vinculo_uuid):
    vinculo = get_object_or_404(EmpreendimentoDocumento, uuid=vinculo_uuid, empreendimento__uuid=empreendimento_uuid)
    # Remove padrão dos outros do mesmo tipo
    EmpreendimentoDocumento.objects.filter(
        empreendimento_id=vinculo.empreendimento_id,
        modelo__tipo=vinculo.modelo.tipo,
        padrao=True,
    ).update(padrao=False)
    vinculo.padrao = True
    vinculo.save(update_fields=['padrao'])
    messages.success(request, f'"{vinculo.modelo.titulo}" definido como padrão.')
    return redirect('detalhe-empreendimento', uuid=vinculo.empreendimento.uuid)
