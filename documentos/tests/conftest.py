import os

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')

User = get_user_model()

_LOGIN_EMAIL = 'admin_documentos@glot.test'
_LOGIN_PASS = 'glotpass123'


@pytest.fixture(scope='session', autouse=True)
def suppress_post_migrate_glot_permissions():
	from accounts.apps import create_glot_permissions
	from django.apps import apps as django_apps
	from django.db.models.signals import post_migrate
	accounts_config = django_apps.get_app_config('accounts')
	post_migrate.disconnect(create_glot_permissions, sender=accounts_config)
	yield
	post_migrate.connect(create_glot_permissions, sender=accounts_config)


@pytest.fixture
def superuser(transactional_db):
	user = User(
		username=_LOGIN_EMAIL,
		email=_LOGIN_EMAIL,
		first_name='Admin',
		last_name='Documentos',
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