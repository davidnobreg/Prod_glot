from documentos.models import DocumentoGerado, StatusDocumento

from .models import TIPO_ASSINADO_PARA_GERADO


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
