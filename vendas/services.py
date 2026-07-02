from clientes.models import ClienteDocumento
from documentos.models import DocumentoGerado, StatusDocumento

from .models import TIPO_ASSINADO_PARA_GERADO


def checklist_documentos_cliente(cliente):
	"""Checklist de documentos obrigatórios do cliente (PF/PJ) com status de disponibilidade.

	Usado por PreVendaDetalheView (exibição) e EfetivarVendaView (gate de efetivação) —
	mesma regra de negócio, não duplicar.
	"""
	docs_cliente = ClienteDocumento.objects.filter(cliente=cliente, status='disponivel')
	tipos_disponiveis = set(docs_cliente.values_list('tipo', flat=True))
	tipo_pessoa = 'PJ' if cliente and cliente.documento and len(cliente.documento) == 14 else 'PF'

	docs_obrigatorios = []
	if tipo_pessoa == 'PF':
		if 'CNH' in tipos_disponiveis:
			docs_obrigatorios.append('CNH')
		else:
			docs_obrigatorios += ['RG', 'CPF']
		docs_obrigatorios.append('COMPROVANTE_RESIDENCIA')
		estado_civil = (cliente.estado_civil or '').lower()
		if estado_civil not in ('solteiro', 'solteira'):
			docs_obrigatorios.append('COMPROVANTE_ESTADO_CIVIL')
	else:
		docs_obrigatorios = [
			'CNPJ', 'CONTRATO_SOCIAL', 'RG_CPF_ADMINISTRADOR', 'COMPROVANTE_RESIDENCIA',
		]

	tipo_labels = dict(ClienteDocumento.TIPO_CHOICES)
	checklist = []
	for tipo in docs_obrigatorios:
		doc = docs_cliente.filter(tipo=tipo).first()
		checklist.append({
			'tipo': tipo,
			'label': tipo_labels.get(tipo, tipo),
			'doc': doc,
			'disponivel': doc is not None,
		})
	return checklist


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
