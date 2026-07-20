from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views import View

from empreendimentos.models import Lote
from vendas.models import DistratoVenda, RegisterVenda, validate_documento_assinado
from vendas.views.transferencia_views import _somente_administrador


class IniciarDistratoView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem iniciar distrato.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda.objects.select_related('cliente', 'lote'), uuid=venda_uuid)

		distrato_ativo = venda.distratos.filter(status__in=['INICIADO', 'AGUARDANDO_ASSINATURA']).first()
		if distrato_ativo:
			return redirect('distrato-detalhe', distrato_uuid=distrato_ativo.uuid)

		context = {
			'venda': venda,
			'is_administrativo': False,
		}
		return render(request, 'distrato_iniciar.html', context)

	@transaction.atomic
	def post(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem iniciar distrato.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda.objects.select_for_update(), uuid=venda_uuid)

		if venda.distratos.filter(status__in=['INICIADO', 'AGUARDANDO_ASSINATURA']).exists():
			messages.error(request, "Já existe um distrato em andamento para esta venda.")
			distrato_ativo = venda.distratos.filter(status__in=['INICIADO', 'AGUARDANDO_ASSINATURA']).first()
			return redirect('distrato-detalhe', distrato_uuid=distrato_ativo.uuid)

		distrato = DistratoVenda.objects.create(
			venda=venda,
			motivo=request.POST.get('motivo', ''),
			iniciado_por=request.user,
		)

		venda.status_distrato = 'INICIADO'
		venda.save(update_fields=['status_distrato'])

		messages.success(request, "Distrato iniciado.")
		return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)


class IniciarDistratoAdministrativoView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem iniciar distrato administrativo.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda.objects.select_related('cliente', 'lote'), uuid=venda_uuid)

		distrato_ativo = venda.distratos.filter(status__in=['INICIADO', 'AGUARDANDO_ASSINATURA']).first()
		if distrato_ativo:
			return redirect('distrato-detalhe', distrato_uuid=distrato_ativo.uuid)

		context = {
			'venda': venda,
			'is_administrativo': True,
		}
		return render(request, 'distrato_iniciar.html', context)

	@transaction.atomic
	def post(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem iniciar distrato administrativo.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda.objects.select_for_update(), uuid=venda_uuid)

		if venda.distratos.filter(status__in=['INICIADO', 'AGUARDANDO_ASSINATURA']).exists():
			messages.error(request, "Já existe um distrato em andamento para esta venda.")
			distrato_ativo = venda.distratos.filter(status__in=['INICIADO', 'AGUARDANDO_ASSINATURA']).first()
			return redirect('distrato-detalhe', distrato_uuid=distrato_ativo.uuid)

		motivo_administrativo = request.POST.get('motivo_administrativo', '').strip()
		if not motivo_administrativo:
			messages.error(request, "Motivo administrativo é obrigatório.")
			return redirect('iniciar-distrato-administrativo', venda_uuid=venda.uuid)

		distrato = DistratoVenda.objects.create(
			venda=venda,
			is_administrativo=True,
			motivo_administrativo=motivo_administrativo,
			iniciado_por=request.user,
		)

		venda.status_distrato = 'INICIADO'
		venda.save(update_fields=['status_distrato'])

		messages.success(request, "Distrato administrativo iniciado.")
		return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)


class DetalheDistratoView(LoginRequiredMixin, View):

	def get(self, request, distrato_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem acessar distrato.")
			return redirect('lista-empreendimento')

		distrato = get_object_or_404(
			DistratoVenda.objects.select_related('venda', 'venda__cliente', 'venda__lote', 'documento_gerado'),
			uuid=distrato_uuid,
		)

		context = {
			'distrato': distrato,
			'venda': distrato.venda,
			'pode_concluir': (
				distrato.status == 'AGUARDANDO_ASSINATURA'
				and (distrato.is_administrativo or bool(distrato.termo_assinado))
			),
		}
		return render(request, 'distrato_detalhe.html', context)


class AvancarParaAssinaturaView(LoginRequiredMixin, View):

	def post(self, request, distrato_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem avançar distrato.")
			return redirect('lista-empreendimento')

		distrato = get_object_or_404(DistratoVenda.objects.select_related('venda'), uuid=distrato_uuid)

		if distrato.status != 'INICIADO':
			messages.error(request, "Distrato não está mais iniciado.")
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		with transaction.atomic():
			distrato.status = 'AGUARDANDO_ASSINATURA'
			distrato.save(update_fields=['status'])

			distrato.venda.status_distrato = 'AGUARDANDO_ASSINATURA'
			distrato.venda.save(update_fields=['status_distrato'])

		messages.success(request, "Distrato avançado para aguardando assinatura.")
		return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)


class UploadTermoDistratoView(LoginRequiredMixin, View):

	def post(self, request, distrato_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem enviar termo de distrato.")
			return redirect('lista-empreendimento')

		distrato = get_object_or_404(DistratoVenda, uuid=distrato_uuid)

		if distrato.status != 'AGUARDANDO_ASSINATURA':
			messages.error(request, "Distrato não está aguardando assinatura.")
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		arquivo = request.FILES.get('termo_assinado')
		if not arquivo:
			messages.error(request, 'Arquivo obrigatório.')
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		try:
			validate_documento_assinado(arquivo)
		except ValidationError as exc:
			messages.error(request, ' '.join(exc.messages))
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		distrato.termo_assinado = arquivo
		distrato.save(update_fields=['termo_assinado'])

		messages.success(request, 'Termo de distrato enviado com sucesso.')
		return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)


class ConcluirDistratoView(LoginRequiredMixin, View):

	@transaction.atomic
	def post(self, request, distrato_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem concluir distrato.")
			return redirect('lista-empreendimento')

		distrato = get_object_or_404(
			DistratoVenda.objects.select_for_update().select_related('venda'),
			uuid=distrato_uuid,
		)

		if distrato.status != 'AGUARDANDO_ASSINATURA':
			messages.error(request, "Distrato não está aguardando assinatura.")
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		if not distrato.is_administrativo and not distrato.termo_assinado:
			messages.error(request, "Envie o termo de distrato assinado antes de concluir.")
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		venda = distrato.venda

		distrato.status = 'CONCLUIDO'
		distrato.concluido_por = request.user
		distrato.concluido_em = now()
		distrato.save(update_fields=['status', 'concluido_por', 'concluido_em'])

		venda.tipo_venda = 'DISTRATADA'
		venda.status_distrato = 'CONCLUIDO'
		venda.is_ativo = False
		venda.save(update_fields=['tipo_venda', 'status_distrato', 'is_ativo'])

		if venda.lote_id:
			lote = Lote.objects.select_for_update().get(pk=venda.lote_id)
			lote.situacao = 'DISPONIVEL'
			lote.save(update_fields=['situacao'])

		messages.success(request, "Distrato concluído. Venda distratada e lote disponível.")
		return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)


class CancelarDistratoView(LoginRequiredMixin, View):

	def post(self, request, distrato_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem cancelar distrato.")
			return redirect('lista-empreendimento')

		distrato = get_object_or_404(DistratoVenda.objects.select_related('venda'), uuid=distrato_uuid)

		if distrato.status not in ('INICIADO', 'AGUARDANDO_ASSINATURA'):
			messages.error(request, "Distrato não está mais pendente.")
			return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)

		with transaction.atomic():
			distrato.status = 'CANCELADO'
			distrato.save(update_fields=['status'])

			venda = distrato.venda
			venda.status_distrato = None
			venda.save(update_fields=['status_distrato'])

		messages.success(request, "Distrato cancelado.")
		return redirect('distrato-detalhe', distrato_uuid=distrato.uuid)
