from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from vendas.models import RegisterVenda

from .models import Carne, Parcela
from .services import gerar_carne, registrar_baixa_manual


def _somente_administrador(request):
	return getattr(request.user, 'tipo_usuario', None) == 'ADMINISTRADOR'


def _parse_decimal(valor):
	return Decimal(str(valor).replace(',', '.'))


def _parse_decimal_seguro(valor):
	try:
		return Decimal(str(valor).replace(',', '.'))
	except (InvalidOperation, TypeError):
		return Decimal('0')


def _parse_date(valor):
	return datetime.strptime(valor, '%Y-%m-%d').date()


def _prefixo_contrato(empreendimento):
	if empreendimento is None:
		return ''
	if empreendimento.sigla:
		return empreendimento.sigla
	palavras = (empreendimento.nome or '').split()
	return ''.join(palavra[0].upper() for palavra in palavras if palavra)


class ListaCarnesVendaView(LoginRequiredMixin, View):

	def get(self, request, venda_uuid):
		if not _somente_administrador(request):
			messages.error(request, "Apenas administradores podem acessar cobranças.")
			return redirect('lista-empreendimento')

		venda = get_object_or_404(
			RegisterVenda.objects.select_related('cliente', 'lote', 'lote__quadra', 'lote__quadra__empr'),
			uuid=venda_uuid,
		)
		carnes = venda.carnes.prefetch_related('parcelas').all()
		entradas = venda.parcelas.filter(tipo='ENTRADA').order_by('numero_parcela')

		empreendimento = venda.lote.quadra.empr if (venda.lote and venda.lote.quadra) else None
		numero_lote = venda.lote.lote if venda.lote else ''
		prefixo = _prefixo_contrato(empreendimento)
		numero_contrato = f'{prefixo}{numero_lote}'

		intercaladas = list(venda.intercaladas.all())
		valor_geral_intercaladas = sum(
			(_parse_decimal_seguro(i.valor_intercalada) * (i.quantidade_parcelas_intercalada or 0) for i in intercaladas),
			Decimal('0'),
		)
		quantidade_intercaladas = sum((i.quantidade_parcelas_intercalada or 0) for i in intercaladas)
		quantidade_intercaladas_pagas = entradas.filter(status='PAGA').count()

		valor_financiado_total = venda.valor_financiado or Decimal('0')

		parcelas_carnes = Parcela.objects.filter(venda=venda, tipo='PARCELA').select_related('carne').order_by('data_vencimento')

		linhas = []
		saldo_liquidado = Decimal('0')

		for parcela in entradas:
			if parcela.status == 'PAGA' and parcela.valor_pago:
				saldo_liquidado += parcela.valor_pago
			linhas.append({
				'parcela': parcela,
				'numero_documento': f'{numero_contrato}-{parcela.numero_parcela:02d}-IN',
				'saldo_liquidado': saldo_liquidado,
				'saldo_devedor': valor_financiado_total - saldo_liquidado,
			})

		for parcela in parcelas_carnes:
			numero_carne = parcela.carne.numero_carne if parcela.carne else 0
			if parcela.status == 'PAGA' and parcela.valor_pago:
				saldo_liquidado += parcela.valor_pago
			linhas.append({
				'parcela': parcela,
				'numero_documento': f'{numero_contrato}-{numero_carne:02d}-{parcela.numero_parcela:02d}',
				'saldo_liquidado': saldo_liquidado,
				'saldo_devedor': valor_financiado_total - saldo_liquidado,
			})

		total_pago = saldo_liquidado
		saldo_devedor_final = valor_financiado_total - total_pago

		context = {
			'venda': venda,
			'carnes': carnes,
			'entradas': entradas,
			'empreendimento': empreendimento,
			'numero_contrato': numero_contrato,
			'forma_pgto': 'A PRAZO' if (venda.quantidade_parcelas or 0) > 1 else 'À VISTA',
			'valor_financiado_calc': valor_financiado_total + (venda.valor_entrada or Decimal('0')),
			'valor_geral_intercaladas': valor_geral_intercaladas,
			'quantidade_intercaladas': quantidade_intercaladas,
			'quantidade_intercaladas_pagas': quantidade_intercaladas_pagas,
			'periodo_fim': date.today(),
			'linhas': linhas,
			'total_pago': total_pago,
			'saldo_devedor_final': saldo_devedor_final,
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
			'initial': {
				'valor_parcela': venda.valor_parcela,
				'data_primeira_parcela': venda.dt_primeira_parcela,
				'ano_referencia': date.today().year,
			},
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
			'initial': {
				'valor': venda.valor_entrada,
				'quantidade_parcelas': 1,
			},
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
			valor_total = _parse_decimal(request.POST.get('valor', ''))
			data_primeira_parcela = _parse_date(request.POST.get('data_vencimento', ''))
			modalidade = request.POST.get('modalidade', 'BOLETO')
			quantidade_parcelas = int(request.POST.get('quantidade_parcelas', '1'))
		except (TypeError, ValueError, InvalidOperation):
			messages.error(request, "Dados inválidos para geração da entrada.")
			return render(request, 'cobranca/gerar_entrada.html', context)

		if not (1 <= quantidade_parcelas <= 12):
			messages.error(request, "Quantidade de parcelas deve ser entre 1 e 12.")
			return render(request, 'cobranca/gerar_entrada.html', context)

		valor_parcela = (valor_total / quantidade_parcelas).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

		with transaction.atomic():
			ultimo = Parcela.objects.filter(venda=venda, tipo='ENTRADA').aggregate(Max('numero_parcela'))['numero_parcela__max']
			proximo_numero = 0 if ultimo is None else ultimo + 1

			for i in range(quantidade_parcelas):
				Parcela.objects.create(
					carne=None,
					venda=venda,
					tipo='ENTRADA',
					modalidade=modalidade,
					numero_parcela=proximo_numero + i,
					valor=valor_parcela,
					data_vencimento=data_primeira_parcela + relativedelta(months=i),
					status='PENDENTE',
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
