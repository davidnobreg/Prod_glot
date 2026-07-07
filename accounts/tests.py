from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rolepermissions.checkers import has_role

from .forms import UserChangeForm, UserCreationForm


User = get_user_model()


class AccountsFormsTests(TestCase):
    def test_creation_form_sets_username_from_email(self):
        form = UserCreationForm(data={
            'first_name': 'Ana',
            'last_name': 'Silva',
            'email': 'ANA@EXAMPLE.COM',
            'creci': '1234',
            'contato': '(83) 99999-9999',
            'tipo_usuario': 'CORRETOR',
            'is_active': 'on',
            'password1': 'SenhaForte123!',
            'password2': 'SenhaForte123!',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.email, 'ana@example.com')
        self.assertEqual(user.username, 'ana@example.com')
        self.assertTrue(user.check_password('SenhaForte123!'))

    def test_change_form_keeps_username_synced_with_email(self):
        user = User.objects.create_user(
            username='old@example.com',
            email='old@example.com',
            password='SenhaForte123!',
            contato='83999999999',
            tipo_usuario='CORRETOR',
        )

        form = UserChangeForm(data={
            'first_name': 'Ana',
            'last_name': 'Silva',
            'username': 'old@example.com',
            'email': 'new@example.com',
            'creci': '1234',
            'contato': '(83) 98888-7777',
            'tipo_usuario': 'ADMINISTRADOR',
            'is_active': 'on',
            'password': user.password,
        }, instance=user)

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.username, 'new@example.com')


class AccountsViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='SenhaForte123!',
            contato='83999999999',
            tipo_usuario='ADMINISTRADOR',
        )
        self.client.force_login(self.user)

    def test_login_uses_email_username(self):
        self.client.logout()

        response = self.client.post(reverse('login'), {
            'email': 'admin@example.com',
            'senha': 'SenhaForte123!',
        })

        self.assertRedirects(response, reverse('lista-empreendimento'))

    def test_list_filter_tipo_usuario_uses_choice_values(self):
        User.objects.create_user(
            username='corretor@example.com',
            email='corretor@example.com',
            password='SenhaForte123!',
            contato='83988887777',
            tipo_usuario='CORRETOR',
        )

        response = self.client.get(reverse('lista-usuario'), {'tipo_user': 'CORRETOR'})

        self.assertEqual(response.status_code, 200)
        usuarios = list(response.context['usuarios'])
        self.assertEqual(len(usuarios), 1)
        self.assertEqual(usuarios[0].tipo_usuario, 'CORRETOR')

    def test_delete_user_rejects_get(self):
        target = User.objects.create_user(
            username='target@example.com',
            email='target@example.com',
            password='SenhaForte123!',
            contato='83977776666',
            tipo_usuario='CORRETOR',
        )

        response = self.client.get(reverse('delete-usuario', args=[target.uuid]))

        self.assertEqual(response.status_code, 405)
        target.refresh_from_db()
        self.assertTrue(target.is_active)

    def test_delete_user_post_deactivates_user(self):
        target = User.objects.create_user(
            username='target@example.com',
            email='target@example.com',
            password='SenhaForte123!',
            contato='83977776666',
            tipo_usuario='CORRETOR',
        )

        response = self.client.post(reverse('delete-usuario', args=[target.uuid]))

        self.assertRedirects(response, reverse('lista-usuario'))
        target.refresh_from_db()
        self.assertFalse(target.is_active)


class AtualizarRolesCommandTests(TestCase):
    def test_command_assigns_roles_from_tipo_usuario(self):
        admin = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='SenhaForte123!',
            contato='83999999999',
            tipo_usuario='ADMINISTRADOR',
        )
        corretor = User.objects.create_user(
            username='corretor@example.com',
            email='corretor@example.com',
            password='SenhaForte123!',
            contato='83988887777',
            tipo_usuario='CORRETOR',
        )
        proprietario = User.objects.create_user(
            username='proprietario@example.com',
            email='proprietario@example.com',
            password='SenhaForte123!',
            contato='83977776666',
            tipo_usuario='PROPRIETARIO',
        )

        out = StringIO()
        call_command('atualizar_roles', stdout=out)

        self.assertTrue(has_role(admin, 'administrador'))
        self.assertTrue(has_role(corretor, 'corretor'))
        self.assertTrue(has_role(proprietario, 'proprietario'))
        self.assertIn('3/3', out.getvalue())
