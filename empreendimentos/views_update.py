from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from base.models import Endereco

from .forms import (
	EmpresaStep2Form, EmpreendimentoStep3Form, EnderecoForm,
	RepresentanteFormSet, DocumentoRepresentanteForm,
)
from .models import Empreendimento, RepresentanteLegal, DocumentoRepresentante
from . import services as empreendimento_services
from . import forms_update

_WIZARD_UPDATE_SESSION_KEY = 'wizard_update'


def _copiar_logo(logo_origem, instance_destino):
	"""Copia o conteúdo de `logo_origem` (ImageField de outra instância)
	pro `logo` de `instance_destino` via ContentFile — nunca reaproveita o
	mesmo path de storage entre draft e real (cada Empreendimento tem seu
	próprio uuid no path, ver `_upload_logo_empreendimento` em models.py)."""
	if not logo_origem:
		return
	if instance_destino.logo:
		instance_destino.logo.delete(save=False)
	instance_destino.logo.save(
		logo_origem.name.rsplit('/', 1)[-1],
		ContentFile(logo_origem.read()),
		save=False,
	)


def _get_or_create_draft(request, empreendimento_uuid):
	"""Retorna (real, draft). Cria o draft (cópia inativa) na primeira
	chamada dessa sessão pra esse empreendimento; reaproveita nas
	seguintes via ponteiro salvo em `request.session`."""
	real = get_object_or_404(Empreendimento, uuid=empreendimento_uuid, is_ativo=True)

	wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
	session_key = str(empreendimento_uuid)
	draft_uuid = wizard_session.get(session_key, {}).get('draft_uuid')

	if draft_uuid:
		draft = Empreendimento.objects.filter(uuid=draft_uuid, is_ativo=False).first()
		if draft is not None:
			return real, draft

	endereco_empresa = empreendimento_services.sincronizar_endereco(None, real.endereco_empresa)
	endereco_empreendimento = empreendimento_services.sincronizar_endereco(None, real.endereco_empreendimento)

	draft = Empreendimento.objects.create(
		is_ativo=False,
		nome=real.nome,
		telefone=real.telefone,
		observacao=real.observacao,
		cnpj=None,  # nunca copiar: unique=True no banco colide com o do real (ver Global Constraints)
		razaoSocial=real.razaoSocial,
		codBanco=real.codBanco,
		banco=real.banco,
		agencia=real.agencia,
		conta=real.conta,
		matricula=real.matricula,
		cidade_foro=real.cidade_foro,
		tempo_reserva=real.tempo_reserva,
		quantidade_parcela=real.quantidade_parcela,
		desconto=real.desconto,
		tipo_correcao=real.tipo_correcao,
		endereco_empresa=endereco_empresa,
		endereco_empreendimento=endereco_empreendimento,
	)
	_copiar_logo(real.logo, draft)

	wizard_session[session_key] = {'draft_uuid': str(draft.uuid), 'cnpj_pendente': real.cnpj}
	request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
	request.session.modified = True

	return real, draft


def _deletar_draft(request, empreendimento_uuid):
	"""Apaga o draft (+ seus 2 enderecos + logo) e limpa o ponteiro da
	sessão. Não afeta o objeto real de forma alguma."""
	wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
	session_key = str(empreendimento_uuid)
	entrada = wizard_session.get(session_key)
	if entrada is None:
		return

	draft = Empreendimento.objects.filter(uuid=entrada['draft_uuid']).first()
	if draft is not None:
		if draft.endereco_empresa_id:
			Endereco.objects.filter(pk=draft.endereco_empresa_id).delete()
		if draft.endereco_empreendimento_id:
			Endereco.objects.filter(pk=draft.endereco_empreendimento_id).delete()
		if draft.logo:
			draft.logo.delete(save=False)
		draft.delete()

	del wizard_session[session_key]
	request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
	request.session.modified = True


_WIZARD_UPDATE_STEPS = [
	('Dados gerais', 'empreendimento_update_step1'),
	('Empresa', 'empreendimento_update_step2'),
	('Endereço', 'empreendimento_update_step3'),
	('Representantes', 'empreendimento_update_step4'),
	('Configurações', 'empreendimento_update_step5'),
	('Documentos', 'empreendimento_update_step6'),
]


def _wizard_update_render(request, template, current_step, real, context):
	context['wizard_steps'] = _WIZARD_UPDATE_STEPS
	context['current_step'] = current_step
	context['empreendimento'] = real
	return render(request, template, context)


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step1(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST':
		form = forms_update.EmpreendimentoUpdateStep1Form(
			request.POST, request.FILES, instance=draft, real_pk=real.pk,
		)
		if form.is_valid():
			form.save()
			return redirect('empreendimento_update_step2', empreendimento_uuid=empreendimento_uuid)
		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		form = forms_update.EmpreendimentoUpdateStep1Form(instance=draft, real_pk=real.pk)

	return _wizard_update_render(request, 'wizard/update/step1_dados_gerais.html', 1, real, {
		'form': form,
	})


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step2(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	session_key = str(empreendimento_uuid)

	if request.method == 'POST':
		form = forms_update.EmpresaUpdateStep2Form(request.POST, instance=draft, real_pk=real.pk)
		form_endereco = EnderecoForm(request.POST, prefix='empresa', instance=draft.endereco_empresa)

		if form.is_valid() and form_endereco.is_valid():
			cnpj_pendente = form.cleaned_data['cnpj']
			empreendimento = form.save(commit=False)
			empreendimento.cnpj = None  # nunca grava no draft — ver Global Constraints
			empreendimento.endereco_empresa = empreendimento_services.criar_ou_atualizar_endereco(
				form_endereco.cleaned_data, endereco=draft.endereco_empresa
			)
			empreendimento.save()

			wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
			wizard_session[session_key]['cnpj_pendente'] = cnpj_pendente
			request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
			request.session.modified = True

			return redirect('empreendimento_update_step3', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		cnpj_pendente = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {}).get(session_key, {}).get('cnpj_pendente', real.cnpj)
		form = forms_update.EmpresaUpdateStep2Form(instance=draft, real_pk=real.pk, initial={'cnpj': cnpj_pendente})
		form_endereco = EnderecoForm(prefix='empresa', instance=draft.endereco_empresa)

	return _wizard_update_render(request, 'wizard/update/step2_empresa.html', 2, real, {
		'form': form, 'form_endereco': form_endereco,
	})


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step3(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST':
		form = EmpreendimentoStep3Form(request.POST, instance=draft)
		form_endereco = EnderecoForm(request.POST, prefix='empreendimento', instance=draft.endereco_empreendimento)

		if form.is_valid() and form_endereco.is_valid():
			empreendimento = form.save(commit=False)
			empreendimento.endereco_empreendimento = empreendimento_services.criar_ou_atualizar_endereco(
				form_endereco.cleaned_data, endereco=draft.endereco_empreendimento
			)
			empreendimento.save()
			return redirect('empreendimento_update_step4', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		form = EmpreendimentoStep3Form(instance=draft)
		form_endereco = EnderecoForm(prefix='empreendimento', instance=draft.endereco_empreendimento)

	return _wizard_update_render(request, 'wizard/update/step3_endereco.html', 3, real, {
		'form': form, 'form_endereco': form_endereco,
	})


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step4(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	queryset = RepresentanteLegal.objects.filter(empreendimento=real, is_ativo=True).order_by('id')

	if request.method == 'POST':
		formset = RepresentanteFormSet(request.POST, queryset=queryset, prefix='representante')
		enderecos_forms = [
			EnderecoForm(request.POST, prefix=f'representante-{i}-endereco')
			for i in range(len(formset.forms))
		]

		if formset.is_valid() and all(f.is_valid() for f in enderecos_forms):
			for form, form_endereco in zip(formset.forms, enderecos_forms):
				if not form.cleaned_data or form.cleaned_data.get('DELETE'):
					continue
				representante = form.instance
				dados = {k: v for k, v in form.cleaned_data.items() if k != 'id'}
				if representante.pk:
					empreendimento_services.atualizar_representante(
						representante, dados, endereco_dados=form_endereco.cleaned_data
					)
				else:
					empreendimento_services.criar_representante(
						real, dados, endereco_dados=form_endereco.cleaned_data
					)
			return redirect('empreendimento_update_step5', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios dos representantes.')
		docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
		reps_docs = [
			form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
			for form in formset.forms
		]
		return _wizard_update_render(request, 'wizard/update/step4_representantes.html', 4, real, {
			'formset': formset, 'enderecos_forms': enderecos_forms,
			'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
			'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
			'empty_doc_form': DocumentoRepresentanteForm(),
		})

	formset = RepresentanteFormSet(queryset=queryset, prefix='representante')
	enderecos_forms = [
		EnderecoForm(prefix=f'representante-{i}-endereco', instance=form.instance.endereco if form.instance.pk else None)
		for i, form in enumerate(formset.forms)
	]
	docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
	reps_docs = [
		form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
		for form in formset.forms
	]
	return _wizard_update_render(request, 'wizard/update/step4_representantes.html', 4, real, {
		'formset': formset, 'enderecos_forms': enderecos_forms,
		'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
		'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
		'empty_doc_form': DocumentoRepresentanteForm(),
	})


_CAMPOS_STEP5 = ('tempo_reserva', 'quantidade_parcela', 'desconto', 'tipo_correcao')


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step5(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST':
		for campo in _CAMPOS_STEP5:
			if campo in request.POST:
				setattr(draft, campo, request.POST.get(campo))
		try:
			draft.full_clean(validate_unique=False)
			draft.save(update_fields=_CAMPOS_STEP5)
		except ValidationError as e:
			messages.error(request, '; '.join(e.messages) if hasattr(e, 'messages') else str(e))
			return _wizard_update_render(request, 'wizard/update/step5_configuracoes.html', 5, real, {})
		return redirect('empreendimento_update_step6', empreendimento_uuid=empreendimento_uuid)

	return _wizard_update_render(request, 'wizard/update/step5_configuracoes.html', 5, real, {
		'draft': draft,
	})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_cancelar(request, empreendimento_uuid):
	_deletar_draft(request, empreendimento_uuid)
	return redirect('lista-empreendimento-tabela')


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


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_rep_del(request, empreendimento_uuid, rep_uuid):
	representante = get_object_or_404(
		RepresentanteLegal, uuid=rep_uuid, empreendimento__uuid=empreendimento_uuid, empreendimento__is_ativo=True,
	)
	empreendimento_services.desativar_representante(representante)
	return JsonResponse({'ok': True})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_rep_doc_upload(request, empreendimento_uuid, rep_uuid):
	representante = get_object_or_404(
		RepresentanteLegal, uuid=rep_uuid, empreendimento__uuid=empreendimento_uuid, empreendimento__is_ativo=True,
	)
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


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_rep_doc_del(request, empreendimento_uuid, doc_uuid):
	documento = get_object_or_404(
		DocumentoRepresentante, uuid=doc_uuid,
		representante__empreendimento__uuid=empreendimento_uuid,
		representante__empreendimento__is_ativo=True,
	)
	empreendimento_services.remover_documento_representante(documento)
	return JsonResponse({'ok': True})
