from django.apps import AppConfig


MODULOS_GLOT = [
	("vendas", "Vendas"),
	("clientes", "Clientes"),
	("empreendimentos", "Empreendimentos"),
	("documentos", "Documentos"),
	("relatorios", "Relatórios"),
	("usuarios", "Usuários"),
]

ACOES = ["ver", "criar", "editar", "excluir"]


def create_glot_permissions(sender, **kwargs):
	from django.contrib.contenttypes.models import ContentType
	from django.contrib.auth.models import Permission
	from django.apps import apps

	UserModel = apps.get_model('accounts', 'User')
	ct = ContentType.objects.get_for_model(UserModel)

	for codigo, nome in MODULOS_GLOT:
		for acao in ACOES:
			codename = f"glot_{codigo}_{acao}"
			name = f"{nome}: {acao}"
			Permission.objects.get_or_create(
				codename=codename,
				content_type=ct,
				defaults={"name": name},
			)


class AccountsConfig(AppConfig):
	default_auto_field = 'django.db.models.BigAutoField'
	name = 'accounts'

	def ready(self):
		import accounts.signals
		from django.db.models.signals import post_migrate
		post_migrate.connect(create_glot_permissions, sender=self)