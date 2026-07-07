"""Views do módulo de documentos reestruturado (Fase 8).

Views finas — toda regra em services.py. Permissões via rolepermissions.
"""
import json
import os

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from rolepermissions.checkers import has_permission
from rolepermissions.decorators import has_permission_decorator

from empreendimentos.models import Empreendimento
from vendas.models import RegisterVenda

from . import services
from .models import (
	Distrato,
	DocumentoGerado,
	EmpreendimentoDocumento,
	ModeloDocumento,
	StatusDocumento,
	TipoDocumento,
	VariavelDocumento,
)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------
def _variaveis_por_categoria():
	"""Lista de (rotulo_categoria, [variaveis]) para a sidebar do editor."""
	rotulos = dict(VariavelDocumento.CATEGORIAS)
	agrupado = {}
	for v in VariavelDocumento.objects.filter(ativo=True):
		agrupado.setdefault(v.categoria, []).append(v)
	return [(rotulos.get(cat, cat), itens) for cat, itens in agrupado.items()]


def _asset_ver():
	"""Versão dos estáticos do editor (mtime) para cache-busting automático.

	Sem pipeline de build, os arquivos têm nome fixo; o navegador cacheia o
	bundle antigo. O ?v={mtime} força recarga quando o bundle/JS muda.
	"""
	raiz = os.path.join(settings.BASE_DIR, 'documentos', 'static', 'documentos')
	arquivos = [
		os.path.join(raiz, 'js', 'vendor', 'tiptap.bundle.min.js'),
		os.path.join(raiz, 'js', 'editor', 'editor-init.js'),
		os.path.join(raiz, 'js', 'editor', 'variavel-node.js'),
		os.path.join(raiz, 'css', 'documento_a4.css'),
	]
	try:
		return int(max(os.path.getmtime(a) for a in arquivos))
	except OSError:
		return 0


def _contexto_exemplo():
	"""Contexto aninhado a partir dos campos 'exemplo' das variáveis (preview)."""
	ctx = {}
	for v in VariavelDocumento.objects.filter(ativo=True):
		partes = v.tag_slug.split('.')
		alvo = ctx
		for p in partes[:-1]:
			alvo = alvo.setdefault(p, {})
		alvo[partes[-1]] = v.exemplo or f'[{v.tag_slug}]'
	return ctx


# ----------------------------------------------------------
# Modelos
# ----------------------------------------------------------
@has_permission_decorator('documentoModelos')
def modelos_lista(request):
	modelos = ModeloDocumento.objects.all()
	return render(request, 'documentos/modelos_lista.html', {'modelos': modelos})


@has_permission_decorator('documentoModelos')
def modelo_editor(request, modelo_uuid=None):
	modelo = get_object_or_404(ModeloDocumento, uuid=modelo_uuid) if modelo_uuid else None
	salvar_url = reverse('documentos:modelo-salvar', args=[modelo.uuid]) if modelo else reverse('documentos:modelo-salvar-novo')
	conteudo = modelo.conteudo_html if modelo else ''

	empreendimentos_vinculo = []
	if modelo:
		vinculos = EmpreendimentoDocumento.objects.filter(
			modelo=modelo, ativo=True,
		).select_related('empreendimento', 'empreendimento__config_documento')
		for v in vinculos:
			cfg = getattr(v.empreendimento, 'config_documento', None)
			empreendimentos_vinculo.append({
				'uuid': str(v.empreendimento.uuid),
				'nome': v.empreendimento.nome,
				'margem_sup': cfg.margem_sup if cfg else 25,
				'margem_dir': cfg.margem_dir if cfg else 20,
				'margem_inf': cfg.margem_inf if cfg else 20,
				'margem_esq': cfg.margem_esq if cfg else 30,
			})

	return render(request, 'documentos/modelo_editor.html', {
		'modelo': modelo,
		'tipos': TipoDocumento.choices,
		'variaveis_por_categoria': _variaveis_por_categoria(),
		'variaveis_json': json.dumps(list(
			VariavelDocumento.objects.filter(ativo=True).values('tag_slug', 'label', 'categoria')
		)),
		'salvar_url': salvar_url,
		'conteudo_inicial_json': json.dumps(conteudo),
		'asset_ver': str(_asset_ver()),
		'empreendimentos_vinculo': empreendimentos_vinculo,
		'empreendimentos_json': json.dumps(empreendimentos_vinculo),
		# O endpoint que persiste o arrasto da régua (empreendimento_margens_salvar)
		# exige 'documentoConfig'; sem isto, um usuário só com 'documentoModelos'
		# via ruler.setReadOnly() achava que podia arrastar e a persistência
		# falhava (403) silenciosamente no backend (ver Finding I3).
		'pode_editar_margem': has_permission(request.user, 'documentoConfig'),
		'cores_texto': [
			'#000000', '#dc3545', '#fd7e14', '#ffc107',
			'#198754', '#0d6efd', '#6f42c1', '#6c757d',
		],
		'cores_realce': [
			'#fff3cd', '#d1e7dd', '#cfe2ff', '#f8d7da',
			'#e2e3e5', '#ffe5b4', '#d3f9d8', '#e5dbff',
		],
		'fontes_familia': [
			('DejaVu Serif', 'DejaVu Serif'),
			('DejaVu Sans', 'DejaVu Sans'),
			('DejaVu Mono', 'DejaVu Mono'),
			('Liberation Serif', 'Liberation Serif'),
			('Liberation Sans', 'Liberation Sans'),
			('Liberation Mono', 'Liberation Mono'),
			('Times New Roman', 'Times New Roman'),
		],
		'fontes_tamanho': [9, 10, 11, 12, 14, 16, 18, 20, 24],
		'espacamentos_linha': [0.5, 1.0, 1.15, 1.5, 2.0],
	})


@has_permission_decorator('documentoModelos')
def modelo_salvar(request, modelo_uuid=None):
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'erros': ['Método inválido']}, status=405)
	try:
		dados = json.loads(request.body)
	except json.JSONDecodeError:
		return JsonResponse({'ok': False, 'erros': ['JSON inválido']}, status=400)

	conteudo = dados.get('conteudo_html', '')
	erros = services.validar_conteudo_modelo(conteudo)
	if erros:
		return JsonResponse({'ok': False, 'erros': erros}, status=400)

	titulo = (dados.get('titulo') or '').strip() or 'Sem título'
	tipo = dados.get('tipo') or TipoDocumento.OUTROS

	if modelo_uuid:
		modelo = get_object_or_404(ModeloDocumento, uuid=modelo_uuid)
		modelo.titulo = titulo
		modelo.tipo = tipo
		modelo.conteudo_html = conteudo
		modelo._editado_por = request.user
		modelo.save()
	else:
		modelo = ModeloDocumento.objects.create(
			titulo=titulo, tipo=tipo, conteudo_html=conteudo, criado_por=request.user,
		)
	return JsonResponse({
		'ok': True,
		'id': modelo.pk,
		# URL de salvamento já vinculada ao uuid — o autosave de um modelo novo
		# passa a atualizar o mesmo registro em vez de criar duplicatas.
		'salvar_url': reverse('documentos:modelo-salvar', args=[modelo.uuid]),
		'redirect': reverse('documentos:modelos-lista'),
	})


@has_permission_decorator('documentoModelos')
def modelo_preview(request, modelo_uuid):
	modelo = get_object_or_404(ModeloDocumento, uuid=modelo_uuid)
	html = services.renderizar_variaveis(modelo.conteudo_html, _contexto_exemplo())
	return render(request, 'documentos/modelo_preview.html', {'modelo': modelo, 'html': html})


@has_permission_decorator('documentoModelos')
def modelo_duplicar(request, modelo_uuid):
	if request.method != 'POST':
		return redirect('documentos:modelos-lista')
	modelo = get_object_or_404(ModeloDocumento, uuid=modelo_uuid)
	copia = services.duplicar_modelo(modelo, request.user)
	messages.success(request, f'Modelo duplicado: {copia.titulo}')
	return redirect('documentos:modelo-editor', modelo_uuid=copia.uuid)


@has_permission_decorator('documentoModelos')
def modelo_toggle_ativo(request, modelo_uuid):
	"""Alterna ativo/inativo do modelo (nunca deleta). Só POST."""
	if request.method != 'POST':
		return redirect('documentos:modelos-lista')
	modelo = get_object_or_404(ModeloDocumento, uuid=modelo_uuid)
	modelo.ativo = not modelo.ativo
	modelo.save(update_fields=['ativo'])
	estado = 'reativado' if modelo.ativo else 'inativado'
	messages.success(request, f'Modelo {estado}: {modelo.titulo}')
	return redirect('documentos:modelos-lista')


@has_permission_decorator('documentoModelos')
def modelo_historico(request, modelo_uuid):
	modelo = get_object_or_404(ModeloDocumento, uuid=modelo_uuid)
	return render(request, 'documentos/modelo_historico.html', {
		'modelo': modelo,
		'historico': modelo.historico.all(),
	})


# ----------------------------------------------------------
# Geração / documentos
# ----------------------------------------------------------
@has_permission_decorator('documentoGerar')
def gerar_documento(request, venda_pk):
	venda = get_object_or_404(RegisterVenda, pk=venda_pk)
	empreendimento = venda.lote.quadra.empr if venda.lote else None
	modelos = ModeloDocumento.objects.para_empreendimento(empreendimento) if empreendimento else ModeloDocumento.objects.none()

	if request.method == 'POST':
		tipo = request.POST.get('tipo')
		modelo_id = request.POST.get('modelo_id') or None
		try:
			doc = services.gerar_documento_venda(venda, tipo, request.user, modelo_id=modelo_id)
		except (ValidationError, ModeloDocumento.DoesNotExist) as e:
			messages.error(request, str(e))
			return redirect('documentos:gerar-documento', venda_pk=venda.pk)
		return redirect('documentos:documento-detalhe', pk=doc.pk)

	return render(request, 'documentos/gerar_documento.html', {
		'venda': venda,
		'tipos': TipoDocumento.choices,
		'modelos': modelos,
	})


@has_permission_decorator('documentoVisualizar')
def documento_detalhe(request, pk):
	doc = get_object_or_404(DocumentoGerado, pk=pk)
	return render(request, 'documentos/documento_detalhe.html', {'doc': doc})


@has_permission_decorator('documentoFinalizar')
def documento_finalizar(request, pk):
	if request.method != 'POST':
		return redirect('documentos:documento-detalhe', pk=pk)
	doc = get_object_or_404(DocumentoGerado, pk=pk)
	try:
		services.finalizar_documento(doc, request.user)
	except ValidationError as e:
		messages.error(request, str(e))
	return redirect('documentos:documento-detalhe', pk=pk)


@has_permission_decorator('documentoVisualizar')
def documento_status(request, pk):
	doc = get_object_or_404(DocumentoGerado, pk=pk)
	pdf_url = doc.arquivo_pdf.url if doc.arquivo_pdf else None
	return JsonResponse({'status': doc.status, 'pdf_url': pdf_url})


@has_permission_decorator('documentoGerar')
def documento_substituir(request, pk):
	if request.method != 'POST':
		return redirect('documentos:documento-detalhe', pk=pk)
	doc = get_object_or_404(DocumentoGerado, pk=pk)
	if not doc.venda:
		messages.error(request, 'Documento sem venda vinculada.')
		return redirect('documentos:documento-detalhe', pk=pk)
	try:
		novo = services.gerar_documento_venda(
			doc.venda, doc.modelo.tipo, request.user,
			modelo_id=doc.modelo_id, substitui_id=doc.pk,
		)
	except ValidationError as e:
		messages.error(request, str(e))
		return redirect('documentos:documento-detalhe', pk=pk)
	return redirect('documentos:documento-detalhe', pk=novo.pk)


@has_permission_decorator('documentoGerar')
def documento_cancelar(request, pk):
	if request.method != 'POST':
		return redirect('documentos:documento-detalhe', pk=pk)
	doc = get_object_or_404(DocumentoGerado, pk=pk)
	doc.status = StatusDocumento.CANCELADO
	doc.save(update_fields=['status'])
	messages.success(request, 'Documento cancelado.')
	return redirect('documentos:documento-detalhe', pk=pk)


@has_permission_decorator('documentoVisualizar')
def documento_pdf(request, pk):
	doc = get_object_or_404(DocumentoGerado, pk=pk)
	if not doc.arquivo_pdf:
		raise Http404('PDF ainda não gerado.')
	return FileResponse(doc.arquivo_pdf.open('rb'), filename=f'{doc.numero}.pdf')


# ----------------------------------------------------------
# Distratos
# ----------------------------------------------------------
@has_permission_decorator('distratoGerenciar')
def distrato_novo(request, venda_pk):
	venda = get_object_or_404(RegisterVenda, pk=venda_pk)
	if request.method == 'POST':
		distrato = Distrato.objects.create(
			venda=venda,
			cliente=venda.cliente,
			motivo=request.POST.get('motivo', ''),
			data_distrato=request.POST.get('data_distrato'),
			valor_devolucao=request.POST.get('valor_devolucao') or 0,
			percentual_retencao=request.POST.get('percentual_retencao') or 0,
			observacao=request.POST.get('observacao', ''),
			criado_por=request.user,
		)
		messages.success(request, 'Distrato criado.')
		return redirect('documentos:distrato-detalhe', pk=distrato.pk)
	return render(request, 'documentos/distrato_form.html', {'venda': venda})


@has_permission_decorator('distratoGerenciar')
def distrato_detalhe(request, pk):
	distrato = get_object_or_404(Distrato, pk=pk)
	return render(request, 'documentos/distrato_detalhe.html', {'distrato': distrato})


@has_permission_decorator('distratoConcluir')
def distrato_concluir(request, pk):
	if request.method != 'POST':
		return redirect('documentos:distrato-detalhe', pk=pk)
	distrato = get_object_or_404(Distrato, pk=pk)
	try:
		services.concluir_distrato(distrato, request.user)
		messages.success(request, 'Distrato concluído. Venda desativada e lote disponível.')
	except ValidationError as e:
		messages.error(request, str(e))
	return redirect('documentos:distrato-detalhe', pk=pk)


# ----------------------------------------------------------
# Variáveis (referência)
# ----------------------------------------------------------
@has_permission_decorator('documentoModelos')
def variaveis_lista(request):
	return render(request, 'documentos/variaveis_lista.html', {
		'variaveis': VariavelDocumento.objects.all(),
	})


# ----------------------------------------------------------
# Margens de página por empreendimento (régua)
# ----------------------------------------------------------
@has_permission_decorator('documentoConfig')
def empreendimento_margens_salvar(request, empreendimento_uuid):
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'erros': ['Método inválido']}, status=405)
	empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
	try:
		dados = json.loads(request.body)
	except json.JSONDecodeError:
		return JsonResponse({'ok': False, 'erros': ['JSON inválido']}, status=400)

	campos = ('margem_sup', 'margem_dir', 'margem_inf', 'margem_esq')
	if any(campo not in dados for campo in campos):
		return JsonResponse({'ok': False, 'erros': ['Campos de margem ausentes']}, status=400)

	erros = services.atualizar_margens_documento(
		empreendimento,
		margem_sup=dados['margem_sup'],
		margem_dir=dados['margem_dir'],
		margem_inf=dados['margem_inf'],
		margem_esq=dados['margem_esq'],
	)
	if erros:
		return JsonResponse({'ok': False, 'erros': erros}, status=400)
	return JsonResponse({'ok': True})
