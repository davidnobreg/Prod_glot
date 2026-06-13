from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


GRUPOS_PERMISSOES = {
	"Administrador": [
		f"glot_{modulo}_{acao}"
		for modulo in ["vendas", "clientes", "empreendimentos", "documentos", "relatorios", "usuarios"]
		for acao in ["ver", "criar", "editar", "excluir"]
	],
	"Corretor": [
		"glot_vendas_ver",
		"glot_vendas_criar",
		"glot_clientes_ver",
		"glot_clientes_criar",
		"glot_clientes_editar",
		"glot_empreendimentos_ver",
		"glot_documentos_ver",
		"glot_documentos_criar",
		"glot_relatorios_ver",
	],
	"Proprietario": [
		"glot_vendas_ver",
		"glot_empreendimentos_ver",
		"glot_relatorios_ver",
	],
}


class Command(BaseCommand):
	help = "Cria ou sincroniza os grupos padrão do GLOT com suas permissões."

	def handle(self, *args, **kwargs):
		for nome_grupo, codenames in GRUPOS_PERMISSOES.items():
			grupo, criado = Group.objects.get_or_create(name=nome_grupo)
			acao = "Criado" if criado else "Atualizado"

			permissoes = Permission.objects.filter(codename__in=codenames)
			encontradas = permissoes.count()
			esperadas = len(codenames)

			if encontradas < esperadas:
				faltando = set(codenames) - set(permissoes.values_list("codename", flat=True))
				self.stdout.write(self.style.WARNING(
					f"{nome_grupo}: {len(faltando)} permissão(ões) não encontrada(s): {faltando}"
				))
				self.stdout.write(self.style.WARNING(
					"Execute 'python manage.py migrate' para criar as permissões glot_* antes de rodar este command."
				))

			grupo.permissions.add(*permissoes)

			self.stdout.write(self.style.SUCCESS(
				f"{acao} grupo '{nome_grupo}' — {encontradas}/{esperadas} permissões adicionadas."
			))
