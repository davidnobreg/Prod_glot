from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from vendas.models import VendaDocumento


class Command(BaseCommand):
	help = (
		'Reporta VendaDocumento(status=aprovado) duplicados — mais de um aprovado '
		'simultâneo pro mesmo (venda, tipo). Rodar em produção ANTES de aplicar a '
		'migration da UniqueConstraint unico_aprovado_por_venda_tipo, que falha se '
		'existir duplicata. Mantém o aprovado mais recente (aprovado_em desc, id desc '
		'como desempate) e arquiva os demais.'
	)

	def add_arguments(self, parser):
		parser.add_argument(
			'--auto-arquivar', action='store_true', default=False,
			help='Arquiva os duplicados mais antigos, mantendo o mais recente aprovado.',
		)
		parser.add_argument(
			'--dry-run', action='store_true', default=False,
			help='Com --auto-arquivar, simula sem salvar.',
		)

	def handle(self, *args, **options):
		grupos_duplicados = (
			VendaDocumento.objects.filter(status='aprovado')
			.values('venda_id', 'tipo')
			.annotate(n=Count('id'))
			.filter(n__gt=1)
		)

		total_grupos = len(grupos_duplicados)
		self.stdout.write(f'{total_grupos} grupo(s) (venda, tipo) com aprovado duplicado encontrados.')

		total_arquivados = 0
		for grupo in grupos_duplicados:
			docs = list(
				VendaDocumento.objects.filter(
					venda_id=grupo['venda_id'], tipo=grupo['tipo'], status='aprovado',
				)
				.select_related('venda', 'venda__cliente')
				.order_by('-aprovado_em', '-id')
			)
			mantido, duplicatas = docs[0], docs[1:]

			self.stdout.write(
				f'  venda={mantido.venda.uuid} cliente={mantido.venda.cliente} tipo={mantido.tipo} -> '
				f'mantém VendaDocumento#{mantido.pk} (aprovado_em={mantido.aprovado_em})'
			)
			for doc in duplicatas:
				self.stdout.write(
					f'    arquiva VendaDocumento#{doc.pk} (aprovado_em={doc.aprovado_em}) '
					f'{"(dry-run, não salvo)" if options["dry_run"] else ""}'
				)
				if options['auto_arquivar'] and not options['dry_run']:
					with transaction.atomic():
						doc.status = 'arquivado'
						doc.save(update_fields=['status'])
					total_arquivados += 1

		if options['auto_arquivar']:
			self.stdout.write(f'Total arquivado: {total_arquivados}')
		else:
			self.stdout.write('Modo relatório (rode com --auto-arquivar pra aplicar).')
