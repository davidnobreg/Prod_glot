import os

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

# playwright inicia asyncio loop antes de django_db_setup → Django detecta contexto async
# e levanta SynchronousOnlyOperation. Variável desabilita essa guarda nos testes.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')

User = get_user_model()

_LOGIN_EMAIL = 'admin@glot.test'
_LOGIN_PASS = 'glotpass123'


@pytest.fixture(scope='session', autouse=True)
def suppress_post_migrate_glot_permissions():
	"""Desconecta create_glot_permissions do signal post_migrate durante a sessão.

	live_server em pytest-django força transactional_db via _live_server_helper.
	O teardown de TransactionTestCase faz TRUNCATE (flush) entre testes e dispara
	post_migrate. create_glot_permissions usa ContentType em cache stale (id=1)
	que não existe mais após TRUNCATE → FK violation.

	Os testes usam is_superuser=True (SUPERUSER_SUPERPOWERS=True bypassa permissões),
	então o signal não é necessário durante os testes.
	"""
	from accounts.apps import create_glot_permissions
	from django.apps import apps as django_apps
	from django.db.models.signals import post_migrate
	accounts_config = django_apps.get_app_config('accounts')
	post_migrate.disconnect(create_glot_permissions, sender=accounts_config)
	yield
	post_migrate.connect(create_glot_permissions, sender=accounts_config)


@pytest.fixture
def superuser(transactional_db):
	"""Cria superuser via bulk_create sem disparar post_save signals.

	O signal createDefinidorDePermissoes chama assign_role() → get_or_create de Permission
	usando ContentType. Após TRUNCATE, django_content_type está vazio mas o cache ainda tem
	id=1 → FK violation. bulk_create não emite post_save, contornando o problema.
	"""
	user = User(
		username=_LOGIN_EMAIL,
		email=_LOGIN_EMAIL,
		first_name='Admin',
		last_name='Test',
		tipo_usuario='ADMINISTRADOR',
		contato='(83) 99999-9999',
		is_superuser=True,
		is_staff=True,
		is_active=True,
	)
	user.password = make_password(_LOGIN_PASS)
	User.objects.bulk_create([user])
	return User.objects.get(username=_LOGIN_EMAIL)


@pytest.fixture
def logged_browser(page, live_server, superuser):
	page.goto(f'{live_server.url}/')
	page.fill('input[name="email"]', _LOGIN_EMAIL)
	page.fill('input[name="senha"]', _LOGIN_PASS)
	page.click('button[type="submit"]')
	page.wait_for_load_state('networkidle')
	return page
