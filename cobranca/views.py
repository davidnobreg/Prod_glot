from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from vendas.models import RegisterVenda

from .models import Carne, Parcela
from .services import gerar_carne, gerar_entrada, registrar_baixa_manual


def _somente_administrador(request):
	return getattr(request.user, 'tipo_usuario', None) == 'ADMINISTRADOR'


def _parse_decimal(valor):
	return Decimal(str(valor).replace(',', '.'))


def _parse_date(valor):
	return datetime.strptime(valor, '%Y-%m-%d').date()


class ListaCarnesVendaView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem acessar cobranças.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda.objects.select_related('cliente', 'lote'), uuid=venda_uuid)
		carnes = venda.carnes.prefetch_related('parcelas').all()
		entradas = venda.parcelas.filter(tipo='ENTRADA')

		context = {
			'venda': venda,
			'carnes': carnes,
			'entradas': entradas,
		}
		return render(request, 'cobranca/lista_carnes.html', context)


class GerarCarneView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem gerar carnê.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
		context = {
			'venda': venda,
			'modalidade_choices': Parcela.MODALIDADE_CHOICES,
		}
		return render(request, 'cobranca/gerar_carne.html', context)

	def post(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem gerar carnê.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
		context = {
			'venda': venda,
			'modalidade_choices': Parcela.MODALIDADE_CHOICES,
		}

		try:
			numero_parcelas = int(request.POST.get('numero_parcelas'))
			valor_parcela = _parse_decimal(request.POST.get('valor_parcela', ''))
			data_primeira_parcela = _parse_date(request.POST.get('data_primeira_parcela', ''))
			ano_referencia = int(request.POST.get('ano_referencia'))
			modalidade = request.POST.get('modalidade', 'BOLETO')
		except (TypeError, ValueError, InvalidOperation):
			messages.error(request, "Dados inválidos para geração do carnê.")
			return render(request, 'cobranca/gerar_carne.html', context)

		try:
			carne = gerar_carne(
				venda=venda,
				numero_parcelas=numero_parcelas,
				valor_parcela=valor_parcela,
				data_primeira_parcela=data_primeira_parcela,
				ano_referencia=ano_referencia,
				usuario=request.user,
				modalidade=modalidade,
			)
		except ValueError as exc:
			messages.error(request, str(exc))
			return render(request, 'cobranca/gerar_carne.html', context)

		messages.success(request, "Carnê gerado com sucesso.")
		return redirect('detalhe_carne', carne_uuid=carne.uuid)


class GerarEntradaView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem gerar entrada.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
		context = {
			'venda': venda,
			'modalidade_choices': Parcela.MODALIDADE_CHOICES,
		}
		return render(request, 'cobranca/gerar_entrada.html', context)

	def post(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem gerar entrada.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
		context = {
			'venda': venda,
			'modalidade_choices': Parcela.MODALIDADE_CHOICES,
		}

		try:
			valor = _parse_decimal(request.POST.get('valor', ''))
			data_vencimento = _parse_date(request.POST.get('data_vencimento', ''))
			modalidade = request.POST.get('modalidade', 'BOLETO')
		except (TypeError, ValueError, InvalidOperation):
			messages.error(request, "Dados inválidos para geração da entrada.")
			return render(request, 'cobranca/gerar_entrada.html', context)

		gerar_entrada(
			venda=venda,
			valor=valor,
			data_vencimento=data_vencimento,
			usuario=request.user,
			modalidade=modalidade,
		)

		messages.success(request, "Entrada gerada com sucesso.")
		return redirect('lista_carnes_venda', venda_uuid=venda.uuid)


class DetalheCarneView(LoginRequiredMixin, View):

	def get(self, request, carne_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem acessar cobranças.")
			return redirect('lista-empreendimento')

		carne = get_object_or_404(
			Carne.objects.select_related('venda', 'venda__cliente', 'venda__lote'),
			uuid=carne_uuid,
		)
		parcelas = carne.parcelas.all()

		context = {
			'carne': carne,
			'venda': carne.venda,
			'parcelas': parcelas,
		}
		return render(request, 'cobranca/detalhe_carne.html', context)


class BaixaManualParcelaView(LoginRequiredMixin, View):

	def get(self, request, parcela_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem registrar baixa manual.")
			return redirect('lista-empreendimento')

		parcela = get_object_or_404(Parcela.objects.select_related('venda', 'carne'), uuid=parcela_uuid)
		context = {'parcela': parcela}
		return render(request, 'cobranca/baixa_manual.html', context)

	def post(self, request, parcela_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem registrar baixa manual.")
			return redirect('lista-empreendimento')

		parcela = get_object_or_404(Parcela.objects.select_related('venda', 'carne'), uuid=parcela_uuid)
		redirect_destino = (
			redirect('detalhe_carne', carne_uuid=parcela.carne.uuid)
			if parcela.carne_id
			else redirect('lista_carnes_venda', venda_uuid=parcela.venda.uuid)
		)

		try:
			valor_pago = _parse_decimal(request.POST.get('valor_pago', ''))
			data_pagamento = _parse_date(request.POST.get('data_pagamento', ''))
			observacoes = request.POST.get('observacoes', '')
		except (TypeError, ValueError, InvalidOperation):
			messages.error(request, "Dados inválidos para baixa manual.")
			return render(request, 'cobranca/baixa_manual.html', {'parcela': parcela})

		try:
			registrar_baixa_manual(
				parcela=parcela,
				valor_pago=valor_pago,
				data_pagamento=data_pagamento,
				usuario=request.user,
				observacoes=observacoes,
			)
		except ValueError as exc:
			messages.error(request, str(exc))
			return render(request, 'cobranca/baixa_manual.html', {'parcela': parcela})

		messages.success(request, "Baixa manual registrada com sucesso.")
		return redirect_destino


class DetalheParcelaView(LoginRequiredMixin, View):

	def get(self, request, parcela_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem acessar cobranças.")
			return redirect('lista-empreendimento')

		parcela = get_object_or_404(
			Parcela.objects.select_related('venda', 'carne', 'baixado_por'),
			uuid=parcela_uuid,
		)
		cobrancas_bancarias = parcela.cobrancas_bancarias.all()

		context = {
			'parcela': parcela,
			'cobrancas_bancarias': cobrancas_bancarias,
		}
		return render(request, 'cobranca/detalhe_parcela.html', context)
