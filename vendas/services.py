from clientes.models import ClienteDocumento
from documentos.models import DocumentoGerado, StatusDocumento

from .models import TIPO_ASSINADO_PARA_GERADO


def checklist_documentos_cliente(cliente):
	"""Checklist de documentos obrigatórios do cliente (PF/PJ) com status de disponibilidade.

	PF: CNH, ou RG_NOVO (já embute CPF), ou RG+CPF (formato antigo) — nessa ordem de preferência.
	Se casado, o cônjuge segue a mesma regra de alternativas (marcado via `pertence_a='CONJUGE'`
	em ClienteDocumento).

	Usado por PreVendaDetalheView (exibição), CriarVendaView e EfetivarVendaView (gates de
	transição) — mesma regra de negócio, não duplicar.
	"""
	docs_cliente = ClienteDocumento.objects.filter(cliente=cliente, status='disponivel')
	tipo_pessoa = 'PJ' if cliente and cliente.documento and len(cliente.documento) == 14 else 'PF'
	tipo_labels = dict(ClienteDocumento.TIPO_CHOICES)
	checklist = []

	def add_pessoa(pertence_a, sufixo_label):
		docs_pessoa = docs_cliente.filter(pertence_a=pertence_a)
		tipos_disponiveis = set(docs_pessoa.values_list('tipo', flat=True))

		if tipo_pessoa == 'PF':
			if 'CNH' in tipos_disponiveis:
				docs_obrigatorios = ['CNH']
			elif 'RG_NOVO' in tipos_disponiveis:
				docs_obrigatorios = ['RG_NOVO']
			else:
				docs_obrigatorios = ['RG', 'CPF']
			if pertence_a == 'TITULAR':
				docs_obrigatorios.append('COMPROVANTE_RESIDENCIA')
				estado_civil = (cliente.estado_civil or '').lower()
				if estado_civil not in ('solteiro', 'solteira'):
					docs_obrigatorios.append('COMPROVANTE_ESTADO_CIVIL')
		else:
			docs_obrigatorios = [
				'CNPJ', 'CONTRATO_SOCIAL', 'RG_CPF_ADMINISTRADOR', 'COMPROVANTE_RESIDENCIA',
			]

		for tipo in docs_obrigatorios:
			doc = docs_pessoa.filter(tipo=tipo).first()
			checklist.append({
				'tipo': tipo,
				'pertence_a': pertence_a,
				'label': f'{tipo_labels.get(tipo, tipo)}{sufixo_label}',
				'doc': doc,
				'disponivel': doc is not None,
			})

	add_pessoa('TITULAR', '')
	if tipo_pessoa == 'PF' and (cliente.estado_civil or '').lower() == 'casado':
		add_pessoa('CONJUGE', ' (Cônjuge)')

	return checklist


def validar_documentos_titular_novo(cliente):
	"""Reaplica checklist_documentos_cliente pro cliente_novo de uma
	TransferenciaTitularidade — mesma regra de negócio usada como gate
	de CriarVendaView/EfetivarVendaView, não duplicar.
	"""
	checklist = checklist_documentos_cliente(cliente)
	completo = all(item['disponivel'] for item in checklist)
	return checklist, completo


def documento_gerado_mais_recente(venda, tipo_assinado):
	"""DocumentoGerado FINALIZADO mais recente pro tipo assinado correspondente
	(proposta_assinada -> proposta, contrato_assinado -> contrato).

	Critério único: criado_em desc, id desc como desempate (evita ordem indefinida
	quando dois DocumentoGerado têm o mesmo criado_em). Usado tanto no auto-link do
	upload (VendaDocumentoUploadView) quanto no backfill (vincular_documentos_pendentes)
	— não duplicar essa lógica em outro lugar.
	"""
	tipo_gerado = TIPO_ASSINADO_PARA_GERADO.get(tipo_assinado)
	if not tipo_gerado:
		return None
	return (
		DocumentoGerado.objects.filter(
			venda=venda, modelo__tipo=tipo_gerado, status=StatusDocumento.FINALIZADO,
		)
		.order_by('-criado_em', '-id')
		.first()
	)
