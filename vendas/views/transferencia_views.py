from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views import View

from clientes.models import Cliente, ClienteTelefone
from documentos.models import DocumentoGerado, ModeloDocumento, StatusDocumento, TipoDocumento
from documentos.views_gerar import _tipos_disponiveis
from vendas.models import (
	HistoricoTitularidade,
	RegisterVenda,
	TransferenciaTitularidade,
	validate_documento_assinado,
)
from vendas.services import validar_documentos_titular_novo


def _somente_administrador(request):
	return getattr(request.user, 'tipo_usuario', None) == 'ADMINISTRADOR'


class IniciarTransferenciaView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem iniciar transferência de titularidade.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(
			RegisterVenda.objects.select_related('cliente', 'lote'),
			uuid=venda_uuid,
		)

		if venda.transferencias.filter(status='PRE_TRANSFERENCIA').exists():
			transferencia = venda.transferencias.filter(status='PRE_TRANSFERENCIA').first()
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		context = {
			'venda': venda,
			'cliente_anterior': venda.cliente,
			'clientes_disponiveis': Cliente.objects.filter(is_ativo=True).exclude(pk=venda.cliente_id).order_by('name'),
			'novo_cliente_id': request.GET.get('novo_cliente_id', ''),
		}
		return render(request, 'transferencia_iniciar.html', context)

	@transaction.atomic
	def post(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem iniciar transferência de titularidade.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(
			RegisterVenda.objects.select_for_update(),
			uuid=venda_uuid,
		)

		if not venda.cliente:
			messages.error(request, "Venda sem titular atual — não é possível iniciar transferência.")
			return redirect('reservado', lote_uuid=venda.lote.uuid)

		if venda.transferencias.filter(status='PRE_TRANSFERENCIA').exists():
			messages.error(request, "Já existe uma transferência em andamento para esta venda.")
			transferencia = venda.transferencias.filter(status='PRE_TRANSFERENCIA').first()
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		cliente_novo = None
		cliente_novo_id = request.POST.get('cliente_novo_id')
		if cliente_novo_id:
			cliente_novo = get_object_or_404(Cliente, uuid=cliente_novo_id)

		transferencia = TransferenciaTitularidade.objects.create(
			venda=venda,
			cliente_anterior=venda.cliente,
			cliente_novo=cliente_novo,
			iniciado_por=request.user,
		)

		venda.status_transferencia = 'PRE_TRANSFERENCIA'
		venda.save(update_fields=['status_transferencia'])

		messages.success(request, "Transferência de titularidade iniciada.")
		return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)


class DetalheTransferenciaView(LoginRequiredMixin, View):

	def get(self, request, transferencia_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem acessar transferência de titularidade.")
			return redirect('lista-empreendimento')

		transferencia = get_object_or_404(
			TransferenciaTitularidade.objects.select_related(
				'venda', 'cliente_anterior', 'cliente_novo', 'documento_gerado',
			),
			uuid=transferencia_uuid,
		)

		novo_cliente_id = request.GET.get('novo_cliente_id')
		if novo_cliente_id and transferencia.status == 'PRE_TRANSFERENCIA':
			cliente_novo = get_object_or_404(Cliente, uuid=novo_cliente_id)
			transferencia.cliente_novo = cliente_novo
			transferencia.save(update_fields=['cliente_novo'])

		checklist, checklist_completo = (
			validar_documentos_titular_novo(transferencia.cliente_novo)
			if transferencia.cliente_novo else ([], False)
		)

		venda = transferencia.venda
		empreendimento = getattr(getattr(venda.lote, 'quadra', None), 'empr', None)
		_tipos_ok = _tipos_disponiveis(request.user, venda)

		modelos_por_tipo = {}
		if empreendimento:
			for tipo in TipoDocumento:
				if tipo.value not in _tipos_ok:
					continue
				modelos = ModeloDocumento.objects.para_empreendimento(empreendimento, tipo=tipo.value)
				if modelos.exists():
					padrao = ModeloDocumento.objects.padrao_para(empreendimento, tipo.value)
					modelos_por_tipo[tipo.value] = {
						'label': tipo.label,
						'modelos': list(modelos.values('id', 'titulo', 'versao')),
						'padrao_id': padrao.pk if padrao else None,
					}

		docs_existentes = (
			DocumentoGerado.objects.filter(venda=venda, modelo__tipo__in=_tipos_ok)
			.exclude(status=StatusDocumento.CANCELADO)
			.order_by('-criado_em')
		)

		context = {
			'modelos_por_tipo': modelos_por_tipo,
			'docs_existentes': docs_existentes,
			'transferencia': transferencia,
			'venda': transferencia.venda,
			'cliente_anterior': transferencia.cliente_anterior,
			'cliente_novo': transferencia.cliente_novo,
			'contato_cliente_anterior': ClienteTelefone.objects.filter(cliente=transferencia.cliente_anterior).first(),
			'contato_cliente_novo': (
				ClienteTelefone.objects.filter(cliente=transferencia.cliente_novo).first()
				if transferencia.cliente_novo else None
			),
			'checklist_titular_novo': checklist,
			'checklist_completo': checklist_completo,
			'pode_efetivar': (
				transferencia.status == 'PRE_TRANSFERENCIA'
				and checklist_completo
				and bool(transferencia.arquivo_termo_assinado)
			),
			'clientes_disponiveis': (
				Cliente.objects.filter(is_ativo=True)
				.exclude(pk=transferencia.cliente_anterior_id)
				.order_by('name')
			),
			'historico_titularidade': (
				HistoricoTitularidade.objects.filter(venda=transferencia.venda)
				.select_related('cliente', 'transferencia_origem')
				.order_by('dt_inicio')
			),
		}
		return render(request, 'transferencia_detalhe.html', context)


class EfetivarTransferenciaView(LoginRequiredMixin, View):

	@transaction.atomic
	def post(self, request, transferencia_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem efetivar transferência de titularidade.")
			return redirect('lista-empreendimento')

		transferencia = get_object_or_404(
			TransferenciaTitularidade.objects.select_for_update().select_related('venda'),
			uuid=transferencia_uuid,
		)

		if transferencia.status != 'PRE_TRANSFERENCIA':
			messages.error(request, "Transferência não está mais pendente.")
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		if not transferencia.cliente_novo:
			messages.error(request, "Selecione o novo titular antes de efetivar.")
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		_checklist, checklist_completo = validar_documentos_titular_novo(transferencia.cliente_novo)
		if not checklist_completo:
			messages.error(request, "Checklist de documentos do novo titular incompleto.")
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		if not transferencia.arquivo_termo_assinado:
			messages.error(request, "Envie o termo de transferência assinado antes de efetivar.")
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		venda = transferencia.venda
		hoje = date.today()

		HistoricoTitularidade.objects.filter(
			venda=venda, cliente=transferencia.cliente_anterior, dt_fim__isnull=True,
		).update(dt_fim=hoje)

		HistoricoTitularidade.objects.create(
			venda=venda,
			cliente=transferencia.cliente_novo,
			dt_inicio=hoje,
			dt_fim=None,
			transferencia_origem=transferencia,
		)

		venda.cliente = transferencia.cliente_novo
		venda.status_transferencia = 'TRANSFERENCIA_CONCLUIDA'
		venda.save(update_fields=['cliente', 'status_transferencia'])

		transferencia.status = 'CONCLUIDA'
		transferencia.efetivado_por = request.user
		transferencia.efetivado_em = now()
		transferencia.save(update_fields=['status', 'efetivado_por', 'efetivado_em'])

		messages.success(request, "Transferência de titularidade efetivada com sucesso.")
		return redirect('reservado', lote_uuid=venda.lote.uuid)


class CancelarTransferenciaView(LoginRequiredMixin, View):

	def post(self, request, transferencia_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem cancelar transferência de titularidade.")
			return redirect('lista-empreendimento')

		transferencia = get_object_or_404(
			TransferenciaTitularidade.objects.select_related('venda'),
			uuid=transferencia_uuid,
		)

		if transferencia.status != 'PRE_TRANSFERENCIA':
			messages.error(request, "Transferência não está mais pendente.")
			return redirect('reservado', lote_uuid=transferencia.venda.lote.uuid)

		with transaction.atomic():
			transferencia.status = 'CANCELADA'
			transferencia.save(update_fields=['status'])

			venda = transferencia.venda
			venda.status_transferencia = None
			venda.save(update_fields=['status_transferencia'])

		messages.success(request, "Transferência de titularidade cancelada.")
		return redirect('reservado', lote_uuid=transferencia.venda.lote.uuid)


class UploadTermoAssinadoView(LoginRequiredMixin, View):

	def post(self, request, transferencia_uuid):
		if not _somente_administrador(request):
			raise Http404

		transferencia = get_object_or_404(TransferenciaTitularidade, uuid=transferencia_uuid)

		if transferencia.status != 'PRE_TRANSFERENCIA':
			messages.error(request, "Transferência não está mais pendente.")
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		arquivo = request.FILES.get('arquivo_termo_assinado')
		if not arquivo:
			messages.error(request, 'Arquivo obrigatório.')
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		try:
			validate_documento_assinado(arquivo)
		except ValidationError as exc:
			messages.error(request, ' '.join(exc.messages))
			return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)

		transferencia.arquivo_termo_assinado = arquivo
		transferencia.save(update_fields=['arquivo_termo_assinado'])

		messages.success(request, 'Termo de transferência enviado com sucesso.')
		return redirect('transferencia-detalhe', transferencia_uuid=transferencia.uuid)
