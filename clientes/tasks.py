from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10, queue='clientes')
def processar_documentos_pendentes(self, cliente_uuid):
	"""
	Verifica documentos com status='processando' para o cliente
	e atualiza para 'disponivel'. Disparado após finalizar wizard de cadastro.
	"""
	from clientes.models import Cliente
	try:
		cliente = Cliente.objects.get(uuid=cliente_uuid)
		docs = cliente.arquivos_cliente.filter(status='processando')
		for doc in docs:
			try:
				_ = doc.arquivo.size
				doc.status = 'disponivel'
				doc.save(update_fields=['status'])
			except Exception as e:
				doc.status = 'erro'
				doc.save(update_fields=['status'])
				logger.error(f"Erro ao verificar doc {doc.pk}: {e}")
	except Cliente.DoesNotExist:
		logger.error(f"Cliente {cliente_uuid} não encontrado na task")
	except Exception as exc:
		raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=10, queue='clientes')
def processar_documentos_representante_pendentes(self, cliente_uuid):
	"""
	Verifica documentos com status='processando' dos representantes do cliente
	(sócios/administradores de PJ) e atualiza para 'disponivel'. Task irmã de
	processar_documentos_pendentes, disparada junto no mesmo on_commit do
	wizard_finalizar — para cliente PF não encontra representantes e não faz nada.
	"""
	from clientes.models import Cliente, RepresentanteDocumento
	try:
		cliente = Cliente.objects.get(uuid=cliente_uuid)
		docs = RepresentanteDocumento.objects.filter(
			representante__cliente=cliente, status='processando'
		)
		for doc in docs:
			try:
				_ = doc.arquivo.size
				doc.status = 'disponivel'
				doc.save(update_fields=['status'])
			except Exception as e:
				doc.status = 'erro'
				doc.save(update_fields=['status'])
				logger.error(f"Erro ao verificar doc representante {doc.pk}: {e}")
	except Cliente.DoesNotExist:
		logger.error(f"Cliente {cliente_uuid} não encontrado na task de representante")
	except Exception as exc:
		raise self.retry(exc=exc)
