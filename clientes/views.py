import json
import re as _re

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from rolepermissions.decorators import has_permission_decorator

from .forms import (
    ClienteConjugeForm,
    ClienteDocumentoForm,
    ClienteEnderecoForm,
    ClienteForm,
    ClienteRepresentanteForm,
    ClienteTelefoneForm,
    ClienteUpdateForm,
    EnderecoRepresentanteForm,
    RepresentanteDocumentoForm,
)
from .models import Cliente, ClienteDocumento, ClienteRepresentante, ClienteTelefone, RepresentanteDocumento


# ===================================================================
# HELPERS
# ===================================================================

def _load_json_payload(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _normalize_telefones(telefones):
    """Retorna lista de strings de numero (compat com formato antigo e novo)."""
    if not isinstance(telefones, list):
        return []
    result = []
    for t in telefones:
        if isinstance(t, str):
            if t.strip():
                result.append(t.strip())
        elif isinstance(t, dict):
            n = (t.get('numero') or '').strip()
            if n:
                result.append(n)
    return result


def _normalize_telefones_rich(telefones):
    """Retorna lista de dicts {numero, tipo, observacao} preservando tipo e observação."""
    if not isinstance(telefones, list):
        return []
    result = []
    for t in telefones:
        if isinstance(t, str):
            if t.strip():
                result.append({'numero': t.strip(), 'tipo': 'celular', 'observacao': ''})
        elif isinstance(t, dict):
            numero = (t.get('numero') or '').strip()
            if numero:
                result.append({
                    'numero': numero,
                    'tipo': t.get('tipo') or 'celular',
                    'observacao': t.get('observacao') or '',
                })
    return result


def _wizard_validar_finalizacao(cliente):
    """Valida se o rascunho tem todos os dados obrigatórios para ser ativado."""
    erros = {}
    for campo in ('name', 'documento', 'email'):
        if not (getattr(cliente, campo, '') or '').strip():
            erros[campo] = 'Campo obrigatório.'
    for campo in ('end_cep', 'end_rua', 'end_numero', 'end_bairro', 'end_cidade', 'end_estado'):
        if not (getattr(cliente, campo, '') or '').strip():
            erros[campo] = 'Campo obrigatório.'
    if not cliente.telefones.exists():
        erros['telefones'] = 'Informe pelo menos um telefone.'
    if (getattr(cliente, 'estado_civil', '') or '').lower() == 'casado':
        if not (getattr(cliente, 'conj_nome', '') or '').strip():
            erros['conj_nome'] = 'Nome do cônjuge é obrigatório.'
    if _get_tipo_pessoa(cliente) == 'PJ':
        from clientes.services import validar_representantes_pj
        erro_representantes = validar_representantes_pj(cliente)
        if erro_representantes:
            erros['representantes'] = erro_representantes
    return erros


def _endereco_preenchido(cleaned_data):
    required = ('end_cep', 'end_rua', 'end_numero', 'end_bairro', 'end_cidade', 'end_estado')
    return all((cleaned_data.get(f) or '').strip() for f in required)


def _get_tipo_pessoa(cliente):
    if cliente and cliente.documento:
        return 'PJ' if len(cliente.documento) == 14 else 'PF'
    return 'PF'


def _serializar_representante(rep):
    endereco = None
    if rep.endereco:
        endereco = {
            'cep': rep.endereco.cep,
            'rua': rep.endereco.rua,
            'numero': rep.endereco.numero,
            'complemento': rep.endereco.complemento,
            'bairro': rep.endereco.bairro,
            'cidade': rep.endereco.cidade,
            'estado': rep.endereco.estado,
        }
    return {
        'uuid': str(rep.uuid),
        'nome': rep.nome,
        'documento': rep.documento,
        'cargo': rep.cargo,
        'estado_civil': rep.get_estado_civil_display(),
        'estado_civil_raw': rep.estado_civil,
        'endereco': endereco,
        'documentos': [
            {
                'uuid': str(d.uuid),
                'tipo_display': d.get_tipo_display(),
                'descricao': d.descricao or '',
                'arquivo_url': d.arquivo.url if d.arquivo else '',
            }
            for d in rep.documentos.all()
        ],
    }


def _render_cliente_form(request, template, form, cliente=None,
                         form_endereco=None, form_conjuge=None,
                         telefones_json='[]', origem='lista', lote_uuid=None):
    tipo_pessoa = _get_tipo_pessoa(cliente)
    documentos = cliente.arquivos_cliente.all().order_by('-criado_em') if cliente else []
    context = {
        'form': form,
        'formConjuge': form_conjuge or ClienteConjugeForm(instance=cliente),
        'formEndereco': form_endereco or ClienteEnderecoForm(instance=cliente),
        'formTelefone': ClienteTelefoneForm(),
        'telefones_json': telefones_json,
        'origem': origem,
        'lote_uuid': lote_uuid,
        'documentos': documentos,
        'tem_processando': documentos.filter(status='processando').exists() if cliente else False,
        'form_doc': ClienteDocumentoForm(tipo_pessoa=tipo_pessoa),
        'tipo_pessoa': tipo_pessoa,
    }
    if cliente is not None:
        context['cliente'] = cliente
    return render(request, template, context)


# ===================================================================
# selectCliente
# ===================================================================

@has_permission_decorator('selectCliente')
def selectCliente(request, cliente_uuid):
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
    data = {
        "uuid": str(cliente.uuid),
        "name": cliente.name,
        "documento": cliente.documento,
        "email": cliente.email,
    }
    return JsonResponse(data)


# ===================================================================
# criarCliente
# ===================================================================

@has_permission_decorator('criarCliente')
def criarCliente(request):
    lote_uuid = request.GET.get('lote_uuid') or request.POST.get('lote_uuid')
    origem = request.GET.get('origem', 'lista')
    next_param = request.GET.get('next', '')
    transferencia_uuid = request.GET.get('transferencia_uuid', '')
    venda_uuid = request.GET.get('venda_uuid', '')

    if request.method == 'POST':
        origem = request.POST.get('origem', origem)
        telefones_json = request.POST.get('telefones_json', '[]')

        form = ClienteForm(request.POST, request.FILES)
        form_endereco = ClienteEnderecoForm(request.POST)
        form_conjuge = ClienteConjugeForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Verifique os campos obrigatórios.")
            return _render_cliente_form(
                request, 'cliente.html', form,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json=telefones_json,
                origem=origem, lote_uuid=lote_uuid,
            )

        if not form_endereco.is_valid() or not _endereco_preenchido(form_endereco.cleaned_data):
            messages.error(request, "Informe um endereço completo para cadastrar o cliente.")
            return _render_cliente_form(
                request, 'cliente.html', form,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json=telefones_json,
                origem=origem, lote_uuid=lote_uuid,
            )

        telefones = _normalize_telefones(_load_json_payload(telefones_json, []))
        if not telefones:
            messages.error(request, "Informe pelo menos um telefone para cadastrar o cliente.")
            return _render_cliente_form(
                request, 'cliente.html', form,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json='[]', origem=origem, lote_uuid=lote_uuid,
            )

        is_casado = form.cleaned_data.get('estado_civil') == 'casado'
        if is_casado:
            if not form_conjuge.is_valid() or not form_conjuge.cleaned_data.get('conj_nome'):
                messages.error(request, "Informe o cônjuge para cadastrar cliente casado.")
                return _render_cliente_form(
                    request, 'cliente.html', form,
                    form_endereco=form_endereco, form_conjuge=form_conjuge,
                    telefones_json=json.dumps(telefones),
                    origem=origem, lote_uuid=lote_uuid,
                )

        with transaction.atomic():
            cliente = form.save(commit=False)
            for field, value in form_endereco.cleaned_data.items():
                setattr(cliente, field, value)
            if is_casado:
                for field, value in form_conjuge.cleaned_data.items():
                    setattr(cliente, field, value)
            cliente.save()

            for numero in telefones:
                if numero:
                    ClienteTelefone.objects.create(cliente=cliente, numero=numero)

        messages.success(request, "Cliente cadastrado com sucesso!")

        if origem == 'reserva' and lote_uuid:
            return redirect('reserva-create', reserva_uuid=lote_uuid)
        from django.urls import reverse as _reverse
        return redirect(_reverse('atualizar-cliente', args=[str(cliente.uuid)]) + '?tab=arquivos')

    context = {
        'form': ClienteForm(),
        'formConjuge': ClienteConjugeForm(),
        'formEndereco': ClienteEnderecoForm(),
        'formTelefone': ClienteTelefoneForm(),
        'origem': origem,
        'lote_uuid': lote_uuid,
        'next': next_param,
        'transferencia_uuid': transferencia_uuid,
        'venda_uuid': venda_uuid,
    }
    return render(request, 'cliente.html', context)


# ===================================================================
# atualizarCliente
# ===================================================================

@has_permission_decorator('alterarCliente')
def atualizarCliente(request, cliente_uuid):
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)

    if request.method == 'GET':
        origem = request.GET.get('origem', 'lista')
        lote_uuid = request.GET.get('lote_uuid', '')
        telefones = list(
            ClienteTelefone.objects
            .filter(cliente=cliente)
            .values_list('numero', flat=True)
        )
        tipo_pessoa = _get_tipo_pessoa(cliente)
        documentos = cliente.arquivos_cliente.all().order_by('-criado_em')
        representantes = []
        if tipo_pessoa == 'PJ':
            representantes = list(
                cliente.representantes.filter(is_ativo=True)
                .select_related('endereco')
                .prefetch_related('documentos')
                .order_by('criado_em')
            )
        return render(request, 'cliente_update.html', {
            'form': ClienteUpdateForm(instance=cliente),
            'cliente': cliente,
            'formConjuge': ClienteConjugeForm(instance=cliente),
            'formEndereco': ClienteEnderecoForm(instance=cliente),
            'telefones_json': json.dumps(telefones),
            'origem': origem,
            'lote_uuid': lote_uuid,
            'documentos': documentos,
            'tem_processando': documentos.filter(status='processando').exists(),
            'form_doc': ClienteDocumentoForm(tipo_pessoa=tipo_pessoa),
            'tipo_pessoa': tipo_pessoa,
            'representantes_json': json.dumps(
                [_serializar_representante(r) for r in representantes]
            ),
        })

    origem = request.POST.get('origem', 'lista')
    lote_uuid = request.POST.get('lote_uuid', '')

    form = ClienteUpdateForm(request.POST, request.FILES, instance=cliente)
    form_endereco = ClienteEnderecoForm(request.POST, instance=cliente)
    form_conjuge = ClienteConjugeForm(request.POST, instance=cliente)

    if not form.is_valid():
        messages.error(request, "Verifique os campos obrigatórios.")
        return _render_cliente_form(
            request, 'cliente_update.html', form, cliente=cliente,
            form_endereco=form_endereco, form_conjuge=form_conjuge,
            telefones_json=request.POST.get('telefones_json', '[]'),
            origem=origem, lote_uuid=lote_uuid,
        )

    if not form_endereco.is_valid() or not _endereco_preenchido(form_endereco.cleaned_data):
        messages.error(request, "O cliente precisa ter um endereço completo.")
        return _render_cliente_form(
            request, 'cliente_update.html', form, cliente=cliente,
            form_endereco=form_endereco, form_conjuge=form_conjuge,
            telefones_json=request.POST.get('telefones_json', '[]'),
            origem=origem, lote_uuid=lote_uuid,
        )

    telefones_json = request.POST.get('telefones_json', '[]')
    telefones_recebidos = _normalize_telefones(_load_json_payload(telefones_json, []))
    if not telefones_recebidos:
        messages.error(request, "O cliente precisa ter pelo menos um telefone.")
        return _render_cliente_form(
            request, 'cliente_update.html', form, cliente=cliente,
            form_endereco=form_endereco, form_conjuge=form_conjuge,
            telefones_json='[]', origem=origem, lote_uuid=lote_uuid,
        )

    estado_civil_final = form.cleaned_data.get('estado_civil')
    is_casado = estado_civil_final == 'casado'
    if is_casado:
        if not form_conjuge.is_valid() or not form_conjuge.cleaned_data.get('conj_nome'):
            messages.error(request, "Informe o cônjuge para cliente casado.")
            return _render_cliente_form(
                request, 'cliente_update.html', form, cliente=cliente,
                form_endereco=form_endereco, form_conjuge=form_conjuge,
                telefones_json=json.dumps(telefones_recebidos),
                origem=origem, lote_uuid=lote_uuid,
            )

    with transaction.atomic():
        cliente_obj = form.save(commit=False)
        for field, value in form_endereco.cleaned_data.items():
            setattr(cliente_obj, field, value)
        if is_casado:
            for field, value in form_conjuge.cleaned_data.items():
                setattr(cliente_obj, field, value)
        else:
            cliente_obj.conj_nome = None
            cliente_obj.conj_numero_rg = None
            cliente_obj.conj_orgao_emissor_rg = None
            cliente_obj.conj_documento = None
            cliente_obj.conj_profissao = None
            cliente_obj.conj_nacionalidade = None
        cliente_obj.save()

        telefones_existentes = list(ClienteTelefone.objects.filter(cliente=cliente_obj))
        numeros_existentes = {t.numero for t in telefones_existentes}
        numeros_recebidos = {n for n in telefones_recebidos if n}

        for numero in numeros_recebidos - numeros_existentes:
            ClienteTelefone.objects.create(cliente=cliente_obj, numero=numero)
        for telefone in telefones_existentes:
            if telefone.numero not in numeros_recebidos:
                telefone.delete()

    messages.success(request, "Cliente atualizado com sucesso!")
    if origem == 'reserva' and lote_uuid:
        return redirect('reserva-create', reserva_uuid=lote_uuid)
    return redirect('lista-cliente')


# ===================================================================
# listaCliente
# ===================================================================

@has_permission_decorator('relatorioCliente')
def listaCliente(request):
    clientes_qs = Cliente.objects.filter(
        is_ativo=True
    ).prefetch_related(
        Prefetch(
            'telefones',
            queryset=ClienteTelefone.objects.filter(is_ativo=True),
            to_attr='telefones_list',
        )
    ).order_by('name')

    get_client = request.GET.get('client')
    if get_client:
        clientes_qs = clientes_qs.filter(
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(email__icontains=get_client)
        )

    paginator = Paginator(clientes_qs, 12)
    page_number = request.GET.get('page')
    cliente_obj = paginator.get_page(page_number)

    return render(request, 'lista_cliente.html', {
        'cliente_obj': cliente_obj,
        'clientes': cliente_obj.object_list,
    })


# ===================================================================
# listaClienteRelatorio
# ===================================================================

@has_permission_decorator('relatorioClienteRelatorio')
def listaClienteRelatorio(request):
    clientes_qs = Cliente.objects.filter(is_ativo=True).prefetch_related(
        Prefetch(
            'telefones',
            queryset=ClienteTelefone.objects.filter(is_ativo=True),
            to_attr='telefones_list',
        )
    ).order_by('name')

    get_client = request.GET.get('client')
    if get_client:
        clientes_qs = clientes_qs.filter(
            Q(name__icontains=get_client) |
            Q(documento__icontains=get_client) |
            Q(email__icontains=get_client)
        )

    paginator = Paginator(clientes_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_cliente_relatorio.html', {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,
    })




# ===================================================================
# wizard_arquivo_add
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_arquivo_add(request, cliente_uuid):
	"""Adiciona ClienteDocumento a um cliente rascunho. Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	draft = get_object_or_404(Cliente, uuid=cliente_uuid, is_ativo=False)
	tipo_pessoa = _get_tipo_pessoa(draft)
	form = ClienteDocumentoForm(request.POST, request.FILES, tipo_pessoa=tipo_pessoa)

	if form.is_valid():
		doc = form.save(commit=False)
		doc.cliente = draft
		doc.status = 'processando'
		doc.save()
		return JsonResponse({
			'ok': True,
			'doc': {
				'id': doc.id,
				'tipo_display': doc.get_tipo_display(),
				'descricao': doc.descricao or '',
				'arquivo_url': doc.arquivo.url,
			}
		})

	first_error = next(
		(v[0] for v in form.errors.values() if v),
		'Erro ao salvar documento.'
	)
	return JsonResponse({'ok': False, 'error': first_error})


# ===================================================================
# wizard_arquivo_del
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_arquivo_del(request, cliente_uuid, documento_uuid):
	"""Remove ClienteDocumento de um rascunho específico. Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	doc = get_object_or_404(
		ClienteDocumento,
		uuid=documento_uuid,
		cliente__uuid=cliente_uuid,
		cliente__is_ativo=False,
	)
	doc.delete()
	return JsonResponse({'ok': True})


# ===================================================================
# wizard_representante_add
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_representante_add(request, cliente_uuid):
	"""Adiciona ClienteRepresentante a um cliente PJ (rascunho ou já ativo). Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
	form = ClienteRepresentanteForm(request.POST)
	form_endereco = EnderecoRepresentanteForm(request.POST, prefix='endereco')

	if form.is_valid() and form_endereco.is_valid():
		from clientes.services import criar_representante
		try:
			representante = criar_representante(cliente, form.cleaned_data, form_endereco.cleaned_data)
		except ValidationError as e:
			return JsonResponse({'ok': False, 'error': '; '.join(e.messages)})
		endereco_data = None
		if representante.endereco:
			endereco_data = {
				'cep': representante.endereco.cep,
				'rua': representante.endereco.rua,
				'numero': representante.endereco.numero,
				'complemento': representante.endereco.complemento,
				'bairro': representante.endereco.bairro,
				'cidade': representante.endereco.cidade,
				'estado': representante.endereco.estado,
			}
		return JsonResponse({
			'ok': True,
			'representante': {
				'uuid': str(representante.uuid),
				'nome': representante.nome,
				'documento': representante.documento,
				'cargo': representante.cargo,
				'estado_civil': representante.get_estado_civil_display(),
				'estado_civil_raw': representante.estado_civil,
				'endereco': endereco_data,
			}
		})

	first_error = next(
		(v[0] for v in form.errors.values() if v),
		None
	) or next(
		(v[0] for v in form_endereco.errors.values() if v),
		'Erro ao salvar representante.'
	)
	return JsonResponse({'ok': False, 'error': first_error})


# ===================================================================
# wizard_representante_del
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_representante_del(request, cliente_uuid, representante_uuid):
	"""Remove ClienteRepresentante de um cliente (rascunho ou já ativo). Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
	from clientes.services import remover_representante
	remover_representante(representante_uuid, cliente)
	return JsonResponse({'ok': True})


# ===================================================================
# wizard_representante_arquivo_add
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_representante_arquivo_add(request, representante_uuid):
	"""Adiciona RepresentanteDocumento a um representante (cliente rascunho ou já ativo). Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	representante = get_object_or_404(ClienteRepresentante, uuid=representante_uuid)
	form = RepresentanteDocumentoForm(request.POST, request.FILES)

	if form.is_valid():
		doc = form.save(commit=False)
		doc.representante = representante
		doc.status = 'processando'
		doc.save()
		return JsonResponse({
			'ok': True,
			'doc': {
				'uuid': str(doc.uuid),
				'tipo': doc.tipo,
				'tipo_display': doc.get_tipo_display(),
				'pertence_a': doc.pertence_a,
				'descricao': doc.descricao or '',
				'arquivo_url': doc.arquivo.url,
			}
		})

	first_error = next(
		(v[0] for v in form.errors.values() if v),
		'Erro ao salvar documento.'
	)
	return JsonResponse({'ok': False, 'error': first_error})


# ===================================================================
# wizard_representante_arquivo_del
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_representante_arquivo_del(request, documento_uuid):
	"""Remove RepresentanteDocumento de um representante (cliente rascunho ou já ativo). Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	doc = get_object_or_404(RepresentanteDocumento, uuid=documento_uuid)
	doc.delete()
	return JsonResponse({'ok': True})


# ===================================================================
# wizard_salvar_passo — AJAX: cria/atualiza cliente por etapa
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_salvar_passo(request):
	"""Salva uma etapa do wizard via AJAX. Retorna JSON."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	step_id = request.POST.get('step_id', '')
	cliente_uuid = request.POST.get('cliente_uuid', '').strip()

	if step_id == 'step-1':
		return _wizard_save_step1(request, cliente_uuid)
	elif step_id == 'step-2':
		return _wizard_save_conjuge(request, cliente_uuid)
	elif step_id == 'step-4':
		return _wizard_save_endereco(request, cliente_uuid)
	elif step_id == 'step-5':
		return _wizard_save_contatos(request, cliente_uuid)

	return JsonResponse({'ok': False, 'error': f'Step desconhecido: {step_id}'})


def _wizard_get_draft(uuid_str):
	"""Retorna cliente rascunho (is_ativo=False) ou None."""
	if not uuid_str:
		return None
	try:
		import uuid as _uuid_module
		return Cliente.objects.filter(uuid=_uuid_module.UUID(uuid_str), is_ativo=False).first()
	except (ValueError, AttributeError):
		return None


def _wizard_save_step1(request, cliente_uuid):
	instance = _wizard_get_draft(cliente_uuid)

	if instance is None:
		email = request.POST.get('email', '').strip().lower()
		documento = _re.sub(r'[^0-9]', '', request.POST.get('documento', ''))
		if email:
			instance = Cliente.objects.filter(email__iexact=email, is_ativo=False).first()
		if instance is None and documento:
			instance = Cliente.objects.filter(documento=documento, is_ativo=False).first()

	form = ClienteForm(request.POST, instance=instance)
	if form.is_valid():
		with transaction.atomic():
			c = form.save(commit=False)
			c.is_ativo = False
			c.save()
		return JsonResponse({'ok': True, 'uuid': str(c.uuid)})

	errors = {field: list(errs) for field, errs in form.errors.items()}
	return JsonResponse({'ok': False, 'errors': errors})


def _wizard_save_conjuge(request, cliente_uuid):
	cliente = _wizard_get_draft(cliente_uuid)
	if cliente is None:
		return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado. Recarregue a página.'})

	form = ClienteConjugeForm(request.POST, instance=cliente)
	if form.is_valid():
		form.save()
		return JsonResponse({'ok': True})

	errors = {field: list(errs) for field, errs in form.errors.items()}
	return JsonResponse({'ok': False, 'errors': errors})


def _wizard_save_endereco(request, cliente_uuid):
	cliente = _wizard_get_draft(cliente_uuid)
	if cliente is None:
		return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado. Recarregue a página.'})

	form = ClienteEnderecoForm(request.POST, instance=cliente)
	if form.is_valid():
		form.save()
		return JsonResponse({'ok': True})

	errors = {field: list(errs) for field, errs in form.errors.items()}
	return JsonResponse({'ok': False, 'errors': errors})


def _wizard_save_contatos(request, cliente_uuid):
	cliente = _wizard_get_draft(cliente_uuid)
	if cliente is None:
		return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado. Recarregue a página.'})

	telefones_json = request.POST.get('telefones_json', '[]')
	telefones = _normalize_telefones_rich(_load_json_payload(telefones_json, []))

	with transaction.atomic():
		ClienteTelefone.objects.filter(cliente=cliente).delete()
		for t in telefones:
			ClienteTelefone.objects.create(
				cliente=cliente,
				numero=t['numero'],
				tipo=t['tipo'],
				observacao=t['observacao'],
			)

	return JsonResponse({'ok': True})


# ===================================================================
# wizard_finalizar — AJAX: ativa cliente + dispara Celery
# ===================================================================

@has_permission_decorator('criarCliente')
def wizard_finalizar(request, cliente_uuid):
	"""Finaliza wizard: valida, ativa cliente, dispara Celery após commit."""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

	draft = _wizard_get_draft(str(cliente_uuid))
	if draft is None:
		return JsonResponse({'ok': False, 'error': 'Rascunho não encontrado.'}, status=404)

	erros = _wizard_validar_finalizacao(draft)
	if erros:
		return JsonResponse({'ok': False, 'errors': erros}, status=400)

	from clientes.tasks import processar_documentos_pendentes, processar_documentos_representante_pendentes

	with transaction.atomic():
		draft.is_ativo = True
		draft.save(update_fields=['is_ativo'])
		transaction.on_commit(
			lambda: processar_documentos_pendentes.delay(str(draft.uuid))
		)
		transaction.on_commit(
			lambda: processar_documentos_representante_pendentes.delay(str(draft.uuid))
		)

	origem = request.POST.get('origem', 'lista')
	lote_uuid = request.POST.get('lote_uuid', '')
	next_param = request.POST.get('next', '')
	transferencia_uuid = request.POST.get('transferencia_uuid', '')
	venda_uuid = request.POST.get('venda_uuid', '')

	from django.urls import reverse as _reverse
	if next_param == 'transferencia' and transferencia_uuid:
		redirect_url = (
			_reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia_uuid})
			+ f'?novo_cliente_id={draft.uuid}'
		)
	elif next_param == 'transferencia-iniciar' and venda_uuid:
		redirect_url = (
			_reverse('transferencia-iniciar', kwargs={'venda_uuid': venda_uuid})
			+ f'?novo_cliente_id={draft.uuid}'
		)
	elif origem == 'reserva' and lote_uuid:
		redirect_url = _reverse('reserva-create', kwargs={'reserva_uuid': lote_uuid})
	else:
		redirect_url = _reverse('atualizar-cliente', args=[str(draft.uuid)]) + '?tab=arquivos'

	return JsonResponse({'ok': True, 'redirect_url': redirect_url})


# ===================================================================
# adicionar_documento_cliente
# ===================================================================

@has_permission_decorator('alterarCliente')
def adicionar_documento_cliente(request, cliente_uuid):
    cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
    if request.method != 'POST':
        return redirect('atualizar-cliente', cliente_uuid=cliente_uuid)

    tipo_pessoa = _get_tipo_pessoa(cliente)
    form = ClienteDocumentoForm(request.POST, request.FILES, tipo_pessoa=tipo_pessoa)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.cliente = cliente
        doc.save()
        messages.success(request, 'Documento adicionado com sucesso!')
    else:
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, erro)

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('atualizar-cliente', cliente_uuid=cliente_uuid)


# ===================================================================
# excluir_documento_cliente
# ===================================================================

@has_permission_decorator('alterarCliente')
def excluir_documento_cliente(request, documento_uuid):
    if request.method != 'POST':
        raise Http404
    doc = get_object_or_404(ClienteDocumento, uuid=documento_uuid)
    cliente_uuid = doc.cliente.uuid
    doc.delete()
    messages.success(request, 'Documento excluído com sucesso!')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('atualizar-cliente', cliente_uuid=cliente_uuid)


# ===================================================================
# deleteCliente
# ===================================================================

@has_permission_decorator('deletarCliente')
def deleteCliente(request, cliente_uuid):
    try:
        from vendas.models import RegisterVenda
        cliente = get_object_or_404(Cliente, uuid=cliente_uuid)
        if RegisterVenda.objects.filter(cliente=cliente).exclude(tipo_venda='CANCELADA').exists():
            messages.error(request, 'Cliente possui vendas ativas e não pode ser excluído.')
            return redirect('lista-cliente')
        cliente.is_ativo = False
        if cliente.email:
            cliente.email = f"deleted_{cliente.uuid}@example.com"
        cliente.save()
        messages.success(request, "Cliente desativado com sucesso.")
        return redirect('lista-cliente')
    except Exception as e:
        messages.error(request, f"Erro ao desativar cliente: {str(e)}")
        return redirect('lista-cliente')