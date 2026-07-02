from django.core.management.base import BaseCommand
from django.db import transaction

from vendas.models import VendaDocumento, TIPO_ASSINADO_PARA_GERADO
from vendas.services import documento_gerado_mais_recente


class Command(BaseCommand):
	help = (
		'Reporta VendaDocumento(status=aprovado) sem documento_gerado vinculado, tipo '
		'proposta_assinada e/ou contrato_assinado, em vendas RESERVADO/PRE-VENDA ativas. '
		'Rodar em produção ANTES do deploy do gate de contrato (Task 4) e da efetivação '
		'estendida (Task 5).'
	)

	def add_arguments(self, parser):
		parser.add_argument(
			'--tipo', choices=list(TIPO_ASSINADO_PARA_GERADO.keys()), default=None,
			help='Restringe a um tipo (proposta_assinada ou contrato_assinado). '
			     'Sem essa flag, roda os dois.',
		)
		parser.add_argument(
			'--auto-vincular', action='store_true', default=False,
			help='Tenta vincular ao DocumentoGerado FINALIZADO mais recente do tipo correspondente.',
		)
		parser.add_argument(
			'--dry-run', action='store_true', default=False,
			help='Com --auto-vincular, simula sem salvar.',
		)

	def handle(self, *args, **options):
		tipos = [options['tipo']] if options['tipo'] else list(TIPO_ASSINADO_PARA_GERADO.keys())

		docs_risco = (
			VendaDocumento.objects.vigentes()
			.filter(tipo__in=tipos, status='aprovado', documento_gerado__isnull=True)
			.filter(venda__tipo_venda__in=['RESERVADO', 'PRE-VENDA'], venda__is_ativo=True)
			.select_related('venda', 'venda__cliente')
		)

		total = docs_risco.count()
		self.stdout.write(f'{total} VendaDocumento em risco encontrados ({", ".join(tipos)}).')

		com_candidato, vinculados, pendentes = 0, 0, 0
		for doc in docs_risco:
			venda = doc.venda
			# leitura, sempre calculada — independe de --auto-vincular. Só a escrita
			# abaixo (doc.save()) fica atrás do gate.
			candidato = documento_gerado_mais_recente(venda, doc.tipo)

			if candidato:
				com_candidato += 1
				if options['auto_vincular']:
					self.stdout.write(
						f'  venda={venda.uuid} cliente={venda.cliente} tipo={doc.tipo} -> '
						f'DocumentoGerado {candidato.numero} '
						f'{"(dry-run, não salvo)" if options["dry_run"] else "(vinculado)"}'
					)
					if not options['dry_run']:
						vinculados += 1
						with transaction.atomic():
							doc.documento_gerado = candidato
							doc.save(update_fields=['documento_gerado'])
				else:
					self.stdout.write(
						f'  venda={venda.uuid} cliente={venda.cliente} tipo={doc.tipo} -> '
						f'candidato encontrado: DocumentoGerado {candidato.numero} '
						f'(rode com --auto-vincular pra aplicar)'
					)
			else:
				pendentes += 1
				self.stdout.write(
					f'  venda={venda.uuid} cliente={venda.cliente} tipo_venda={venda.tipo_venda} '
					f'tipo={doc.tipo} VendaDocumento#{doc.pk} -> SEM CANDIDATO, decisão manual necessária'
				)

		if options['auto_vincular']:
			self.stdout.write(
				f'Total: {total} | com candidato: {com_candidato} | '
				f'vinculados agora: {vinculados} | pendentes de decisão manual: {pendentes}'
			)
		else:
			self.stdout.write(
				f'Total: {total} | com candidato disponível: {com_candidato} | '
				f'sem candidato (decisão manual): {pendentes}'
			)
