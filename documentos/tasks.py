from celery import shared_task
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from .pdf_engine import render_pdf


@shared_task
def debug_task():
	"""Task de teste — valida que o worker está ativo."""
	return 'ok'


@shared_task(bind=True, max_retries=3, default_retry_delay=10, queue='pdf')
def gerar_pdf_documento(self, documento_id):
	from .models import DocumentoGerado, StatusDocumento

	doc = DocumentoGerado.objects.select_related('modelo', 'venda').get(pk=documento_id)
	try:
		empreendimento = (
			doc.venda.lote.quadra.empr
			if doc.venda and doc.venda.lote else None
		)
		cfg = getattr(empreendimento, 'config_documento', None) if empreendimento else None

		html_str = render_to_string('documentos/pdf/documento_base.html', {
			'doc': doc,
			'cfg': cfg,
		})

		css_path = finders.find('documentos/css/documento_a4.css')

		base_url = (
			settings.MEDIA_URL
			if getattr(settings, 'USE_REMOTE_STORAGE', False)
			else str(settings.MEDIA_ROOT)
		)
		pdf_bytes = render_pdf(html_str, css_path, base_url, cfg=cfg)

		doc.arquivo_pdf.save(f'{doc.numero}.pdf', ContentFile(pdf_bytes), save=False)
		doc.status = StatusDocumento.FINALIZADO
		doc.finalizado_em = timezone.now()
		doc.save()
	except Exception as exc:
		if self.request.retries >= self.max_retries:
			doc.status = StatusDocumento.ERRO
			doc.save(update_fields=['status'])
		else:
			doc.status = StatusDocumento.RASCUNHO
			doc.save(update_fields=['status'])
		raise self.retry(exc=exc)
