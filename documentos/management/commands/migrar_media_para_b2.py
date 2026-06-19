"""
Management command: migrar_media_para_b2

Migra arquivos salvos localmente em MEDIA_ROOT para o bucket Backblaze B2,
mantendo a mesma estrutura de paths. Não apaga arquivos locais.

Uso:
  python manage.py migrar_media_para_b2 --dry-run
  python manage.py migrar_media_para_b2 --apenas-app empreendimentos
  python manage.py migrar_media_para_b2
"""
import os

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


# ---------------------------------------------------------------
# Mapa de todos os campos de arquivo do projeto
# (app_label, ModelName, [campos])
# ---------------------------------------------------------------
CAMPOS_ARQUIVO = [
	('empreendimentos', 'Empreendimento', ['logo']),
	('clientes', 'Cliente', [
		'foto_rg_frente',
		'foto_rg_verso',
		'foto_cpf',
		'comprovante_residencia',
	]),
	('documentos', 'ConfiguracaoDocumento', ['logo']),
	('documentos', 'DocumentoGerado', ['arquivo_pdf', 'arquivo_word']),
	('cobranca', 'Cobranca', ['url_pdf']),
]


class Command(BaseCommand):
	help = 'Migra arquivos de media/ local para o bucket Backblaze B2'

	def add_arguments(self, parser):
		parser.add_argument(
			'--dry-run',
			action='store_true',
			default=False,
			help='Simula a migração sem enviar nenhum arquivo',
		)
		parser.add_argument(
			'--apenas-app',
			type=str,
			default=None,
			metavar='APP',
			help='Migrar somente um app (ex: empreendimentos, clientes, documentos)',
		)

	def handle(self, *args, **options):
		dry_run = options['dry_run']
		apenas_app = options.get('apenas_app')
		media_root = str(settings.MEDIA_ROOT)

		if dry_run:
			self.stdout.write(self.style.WARNING('=== DRY-RUN: nenhum arquivo será enviado ===\n'))

		if apenas_app:
			apps_validos = {a for a, _, _ in CAMPOS_ARQUIVO}
			if apenas_app not in apps_validos:
				raise CommandError(
					f'App "{apenas_app}" não encontrado no mapa. '
					f'Opções: {", ".join(sorted(apps_validos))}'
				)

		total = ok = ja_no_b2 = sem_local = erros = 0

		for app_label, model_name, campos in CAMPOS_ARQUIVO:
			if apenas_app and app_label != apenas_app:
				continue

			try:
				Model = apps.get_model(app_label, model_name)
			except LookupError:
				self.stdout.write(self.style.WARNING(
					f'[SKIP] {app_label}.{model_name} não encontrado'
				))
				continue

			for campo in campos:
				qs = (
					Model.objects
					.exclude(**{f'{campo}__isnull': True})
					.exclude(**{f'{campo}__exact': ''})
				)
				count = qs.count()
				self.stdout.write(
					f'\n► {app_label}.{model_name}.{campo}  ({count} registro(s) com arquivo)'
				)

				for obj in qs.iterator():
					field_file = getattr(obj, campo)
					relative_path = str(field_file.name)
					local_path = os.path.join(media_root, relative_path)
					total += 1

					# 1. Arquivo existe localmente?
					if not os.path.isfile(local_path):
						self.stdout.write(f'  ✗ SEM LOCAL  {relative_path}')
						sem_local += 1
						continue

					# 2. Já existe no B2?
					try:
						existe_b2 = default_storage.exists(relative_path)
					except Exception as exc:
						self.stdout.write(self.style.ERROR(
							f'  ERRO ao checar B2  {relative_path} — {exc}'
						))
						erros += 1
						continue

					if existe_b2:
						self.stdout.write(f'  ↑ JÁ NO B2  {relative_path}')
						ja_no_b2 += 1
						continue

					# 3. Dry-run: apenas reportar
					if dry_run:
						tamanho = os.path.getsize(local_path)
						self.stdout.write(
							f'  ~ MIGRARIA  {relative_path}  ({tamanho:,} bytes)'
						)
						ok += 1
						continue

					# 4. Upload efetivo
					try:
						with open(local_path, 'rb') as f:
							saved_name = default_storage.save(relative_path, File(f))

						if saved_name != relative_path:
							self.stdout.write(self.style.WARNING(
								f'  ⚠ NOME ALTERADO  {relative_path} → {saved_name}'
							))
						else:
							self.stdout.write(self.style.SUCCESS(
								f'  ✓ OK  {relative_path}'
							))
						ok += 1

					except Exception as exc:
						self.stdout.write(self.style.ERROR(
							f'  ✗ ERRO  {relative_path} — {exc}'
						))
						erros += 1

		# Resumo
		self.stdout.write('\n' + '─' * 50)
		self.stdout.write('RESUMO')
		self.stdout.write('─' * 50)
		self.stdout.write(f'  Avaliados     : {total}')
		if dry_run:
			self.stdout.write(f'  Migrariam     : {ok}')
		else:
			self.stdout.write(f'  Migrados      : {ok}')
		self.stdout.write(f'  Já no B2      : {ja_no_b2}')
		self.stdout.write(f'  Sem arquivo   : {sem_local}')
		self.stdout.write(f'  Erros         : {erros}')
		self.stdout.write('─' * 50)

		if erros:
			raise CommandError(f'{erros} arquivo(s) falharam. Verifique o log acima.')
