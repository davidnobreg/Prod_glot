from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Max

from .models import Carne, Parcela


@transaction.atomic
def gerar_carne(venda, numero_parcelas, valor_parcela, data_primeira_parcela, ano_referencia, usuario, modalidade='BOLETO'):
	if numero_parcelas > 12:
		raise ValueError('Carnê não pode ter mais de 12 parcelas')

	ultimo = Carne.objects.filter(venda=venda).aggregate(Max('numero_carne'))['numero_carne__max']
	numero_carne = (ultimo or 0) + 1

	carne = Carne.objects.create(
		venda=venda,
		numero_carne=numero_carne,
		status='GERADO',
		ano_referencia=ano_referencia,
		gerado_por=usuario,
	)

	for i in range(numero_parcelas):
		Parcela.objects.create(
			carne=carne,
			venda=venda,
			tipo='PARCELA',
			modalidade=modalidade,
			numero_parcela=i + 1,
			valor=valor_parcela,
			data_vencimento=data_primeira_parcela + relativedelta(months=i),
			status='PENDENTE',
		)

	return carne


@transaction.atomic
def gerar_entrada(venda, valor, data_vencimento, usuario, modalidade='BOLETO'):
	return Parcela.objects.create(
		carne=None,
		venda=venda,
		tipo='ENTRADA',
		modalidade=modalidade,
		numero_parcela=0,
		valor=valor,
		data_vencimento=data_vencimento,
		status='PENDENTE',
	)


@transaction.atomic
def registrar_baixa_manual(parcela, valor_pago, data_pagamento, usuario, observacoes=''):
	if parcela.status not in ('PENDENTE', 'INADIMPLENTE'):
		raise ValueError('Parcela não pode ser baixada com status atual')

	parcela.status = 'PAGA'
	parcela.valor_pago = valor_pago
	parcela.data_pagamento = data_pagamento
	parcela.baixado_por = usuario
	if observacoes:
		parcela.observacoes = observacoes
	parcela.save()

	return parcela
