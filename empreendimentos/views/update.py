from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from base.models import Endereco

from ..forms import (
	EnderecoForm, RepresentanteFormSet,
	DocumentoRepresentanteForm, DocumentoEmpreendimentoForm,
	ConfiguracaoGatewayForm,
)
from ..models import Empreendimento, RepresentanteLegal, DocumentoRepresentante, DocumentoEmpreendimento
from .. import services as empreendimento_services
from ..forms import wizard_update as forms_update
from cobranca.models import ConfiguracaoGateway

_WIZARD_UPDATE_SESSION_KEY = 'wizard_update'


def _copiar_logo(logo_origem, instance_destino):
	"""Copia o conteúdo de `logo_origem` (ImageField de outra instância)
	pro `logo` de `instance_destino` via ContentFile — nunca reaproveita o
	mesmo path de storage entre draft e real (cada Empreendimento tem seu
	próprio uuid no path, ver `_upload_logo_empreendimento` em models.py)."""
	if not logo_origem:
		return
	try:
		conteudo = logo_origem.read()
	except FileNotFoundError:
		# referência no banco aponta pra arquivo que não existe mais no
		# storage (dado pré-existente inconsistente) — trata como "sem logo
		# pra copiar" em vez de derrubar a página inteira com 500.
		return
	finally:
		logo_origem.close()  # solta o handle antes que o chamador possa deletar logo_origem (Windows bloqueia delete de arquivo aberto)
	if instance_destino.logo:
		instance_destino.logo.delete(save=False)
	instance_destino.logo.save(
		logo_origem.name.rsplit('/', 1)[-1],
		ContentFile(conteudo),
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
	('Representantes', 'empreendimento_update_step3'),
	('Configurações', 'empreendimento_update_step4'),
	('Revisão', 'empreendimento_update_step5'),
]

CATEGORIAS_UPDATE_STEP1 = (
	'matricula_imovel', 'planta_loteamento', 'memorial_descritivo',
	'registro_loteamento', 'mapa', 'tabela', 'outro',
)
CATEGORIAS_UPDATE_STEP2 = ('contrato_social', 'procuracao', 'alvara', 'licenca_ambiental')


def _doc_form_filtrado(categorias, prefix=None):
	"""DocumentoEmpreendimentoForm com o select de categoria restrito às
	categorias relevantes do step atual (mesmo padrão do wizard de
	cadastro, ver cadastro.py)."""
	doc_form = DocumentoEmpreendimentoForm(prefix=prefix)
	doc_form.fields['categoria'].choices = [
		c for c in doc_form.fields['categoria'].choices if c[0] in categorias
	]
	return doc_form


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
		form_endereco = EnderecoForm(
			request.POST, prefix='empreendimento', instance=draft.endereco_empreendimento,
		)
		if form.is_valid() and form_endereco.is_valid():
			empreendimento = form.save(commit=False)
			empreendimento.endereco_empreendimento = empreendimento_services.criar_ou_atualizar_endereco(
				form_endereco.cleaned_data, endereco=draft.endereco_empreendimento,
			)
			empreendimento.save()
			return redirect('empreendimento_update_step2', empreendimento_uuid=empreendimento_uuid)
		messages.error(request, 'Verifique os campos obrigatórios.')
	else:
		form = forms_update.EmpreendimentoUpdateStep1Form(instance=draft, real_pk=real.pk)
		form_endereco = EnderecoForm(prefix='empreendimento', instance=draft.endereco_empreendimento)

	documentos = real.documentos.filter(categoria__in=CATEGORIAS_UPDATE_STEP1)
	return _wizard_update_render(request, 'wizard/update/step1_dados_gerais.html', 1, real, {
		'form': form, 'form_endereco': form_endereco,
		'documentos': documentos, 'doc_form': _doc_form_filtrado(CATEGORIAS_UPDATE_STEP1, prefix='doclote'),
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

	documentos = real.documentos.filter(categoria__in=CATEGORIAS_UPDATE_STEP2)
	return _wizard_update_render(request, 'wizard/update/step2_empresa.html', 2, real, {
		'form': form, 'form_endereco': form_endereco,
		'documentos': documentos, 'doc_form': _doc_form_filtrado(CATEGORIAS_UPDATE_STEP2),
	})


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step3(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)
	queryset = RepresentanteLegal.objects.filter(empreendimento=real, is_ativo=True).order_by('id')

	if request.method == 'POST':
		formset = RepresentanteFormSet(request.POST, queryset=queryset, prefix='representante')
		enderecos_forms = [
			EnderecoForm(request.POST, prefix=f'representante-{i}-endereco')
			for i in range(len(formset.forms))
		]

		if formset.is_valid() and all(f.is_valid() for f in enderecos_forms):
			try:
				with transaction.atomic():
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
							# mesmo guard do wizard de cadastro (ver cadastro.py::wizard_step3):
							# formset tem min_num=1 com todos os campos opcionais, não cria
							# representante vazio só pra existir.
							representante_vazio = not any(v not in (None, '') for v in dados.values())
							endereco_vazio = not any(v not in (None, '') for v in form_endereco.cleaned_data.values())
							if representante_vazio and endereco_vazio:
								continue
							empreendimento_services.criar_representante(
								real, dados, endereco_dados=form_endereco.cleaned_data
							)
			except ValidationError as exc:
				# full_clean() do RepresentanteLegal (services.criar_representante/
				# atualizar_representante) pode rejeitar dados válidos pro form mas
				# inválidos pro model (ex: CPF duplicado no mesmo empreendimento).
				# Sem isso, a ValidationError subia crua e virava 500 — o
				# transaction.atomic() já desfez qualquer save parcial deste POST
				# antes de re-lançar, então nada fica inconsistente no banco.
				messages.error(
					request,
					'; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
				)
				docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
				reps_docs = [
					form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
					for form in formset.forms
				]
				return _wizard_update_render(request, 'wizard/update/step3_representantes.html', 3, real, {
					'formset': formset, 'enderecos_forms': enderecos_forms,
					'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
					'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
					'empty_doc_form': DocumentoRepresentanteForm(),
				})

			return redirect('empreendimento_update_step4', empreendimento_uuid=empreendimento_uuid)

		messages.error(request, 'Verifique os campos obrigatórios dos representantes.')
		docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
		reps_docs = [
			form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
			for form in formset.forms
		]
		return _wizard_update_render(request, 'wizard/update/step3_representantes.html', 3, real, {
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
	return _wizard_update_render(request, 'wizard/update/step3_representantes.html', 3, real, {
		'formset': formset, 'enderecos_forms': enderecos_forms,
		'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
		'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
		'empty_doc_form': DocumentoRepresentanteForm(),
	})


_CAMPOS_STEP4 = ('tempo_reserva', 'quantidade_parcela', 'desconto', 'tipo_correcao')
_CAMPOS_STEP4_INTEIROS = ('tempo_reserva', 'quantidade_parcela')


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step4(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	# draft nasce sem configuracao_gateway própria (não é copiada em
	# `_get_or_create_draft`, ver Global Constraints do OneToOne) — se o
	# admin ainda não mexeu nela nesta sessão do wizard, cai pro real pra
	# exibir o que já está configurado.
	gateway_instance = getattr(draft, 'configuracao_gateway', None) or getattr(real, 'configuracao_gateway', None)

	if request.method == 'POST':
		for campo in _CAMPOS_STEP4:
			if campo in request.POST:
				valor = request.POST.get(campo)
				if campo in _CAMPOS_STEP4_INTEIROS and valor == '':
					valor = None
				setattr(draft, campo, valor)

		gateway_form = ConfiguracaoGatewayForm(request.POST, prefix='gateway', instance=gateway_instance)

		try:
			draft.full_clean(validate_unique=False)
			draft.save(update_fields=_CAMPOS_STEP4)
		except ValidationError as e:
			messages.error(request, '; '.join(e.messages) if hasattr(e, 'messages') else str(e))
			return _wizard_update_render(request, 'wizard/update/step4_configuracoes.html', 4, real, {
				'draft': draft, 'gateway_form': gateway_form,
			})

		if gateway_form.is_valid():
			dados = gateway_form.dados_preenchidos()
			if dados:
				ConfiguracaoGateway.objects.update_or_create(empreendimento=draft, defaults=dados)

		return redirect('empreendimento_update_step5', empreendimento_uuid=empreendimento_uuid)

	return _wizard_update_render(request, 'wizard/update/step4_configuracoes.html', 4, real, {
		'draft': draft,
		'gateway_form': ConfiguracaoGatewayForm(prefix='gateway', instance=gateway_instance),
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


_CAMPOS_COMMIT_ESCALARES = (
	# 'cnpj' de propósito fora daqui — nunca fica no draft (unique=True no
	# banco), é aplicado à parte via `cnpj_pendente` da sessão (ver abaixo).
	'nome', 'telefone', 'observacao', 'razaoSocial',
	'codBanco', 'banco', 'agencia', 'conta', 'matricula',
	'cidade_foro', 'tempo_reserva', 'quantidade_parcela',
	'desconto', 'tipo_correcao',
)


@has_permission_decorator('alterarEmpreendimento')
def wizard_update_step5(request, empreendimento_uuid):
	real, draft = _get_or_create_draft(request, empreendimento_uuid)

	if request.method == 'POST' and 'finalizar' in request.POST:
		session_key = str(empreendimento_uuid)
		wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
		cnpj_pendente = wizard_session.get(session_key, {}).get('cnpj_pendente', real.cnpj)

		with transaction.atomic():
			for campo in _CAMPOS_COMMIT_ESCALARES:
				setattr(real, campo, getattr(draft, campo))
			real.cnpj = cnpj_pendente

			real.endereco_empresa = empreendimento_services.sincronizar_endereco(
				real.endereco_empresa, draft.endereco_empresa
			)
			real.endereco_empreendimento = empreendimento_services.sincronizar_endereco(
				real.endereco_empreendimento, draft.endereco_empreendimento
			)

			real.full_clean(validate_unique=False)
			real.save()

			draft_gateway = getattr(draft, 'configuracao_gateway', None)
			if draft_gateway is not None:
				ConfiguracaoGateway.objects.update_or_create(
					empreendimento=real,
					defaults={
						'gateway': draft_gateway.gateway,
						'client_id': draft_gateway.client_id,
						'client_secret': draft_gateway.client_secret,
						'convenio': draft_gateway.convenio,
						'certificado': draft_gateway.certificado,
						'chave_certificado': draft_gateway.chave_certificado,
						'sandbox': draft_gateway.sandbox,
					},
				)

		if draft.logo:
			_copiar_logo(draft.logo, real)
			real.save(update_fields=['logo'])

		_deletar_draft(request, empreendimento_uuid)
		messages.success(request, 'Empreendimento atualizado com sucesso.')
		return redirect('lista-empreendimento-tabela')

	session_key = str(empreendimento_uuid)
	cnpj_pendente = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {}).get(session_key, {}).get('cnpj_pendente', real.cnpj)
	representantes = real.representantes.filter(is_ativo=True).prefetch_related('documentos')
	documentos_gerais = real.documentos.filter(categoria__in=CATEGORIAS_UPDATE_STEP1)
	documentos_empresa = real.documentos.filter(categoria__in=CATEGORIAS_UPDATE_STEP2)

	return _wizard_update_render(request, 'wizard/update/step5_revisao.html', 5, real, {
		'draft': draft,
		'cnpj_pendente': cnpj_pendente,
		'representantes': representantes,
		'documentos_gerais': documentos_gerais,
		'documentos_empresa': documentos_empresa,
	})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_doc_upload(request, empreendimento_uuid):
	real = get_object_or_404(Empreendimento, uuid=empreendimento_uuid, is_ativo=True)
	form = DocumentoEmpreendimentoForm(request.POST, request.FILES)
	if not form.is_valid():
		erros = '; '.join(f'{campo}: {", ".join(msgs)}' for campo, msgs in form.errors.items())
		return JsonResponse({'ok': False, 'error': erros}, status=400)

	documento = empreendimento_services.criar_documento_empreendimento(
		real,
		form.cleaned_data['categoria'],
		form.cleaned_data['arquivo'],
		nome=form.cleaned_data.get('nome', ''),
		usuario=request.user,
	)
	return JsonResponse({'ok': True, 'documento': _documento_json(documento)})


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_doc_del(request, empreendimento_uuid, doc_uuid):
	documento = get_object_or_404(
		DocumentoEmpreendimento, uuid=doc_uuid,
		empreendimento__uuid=empreendimento_uuid, empreendimento__is_ativo=True,
	)
	empreendimento_services.remover_documento_empreendimento(documento)
	return JsonResponse({'ok': True})
