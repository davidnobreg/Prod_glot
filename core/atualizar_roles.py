from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rolepermissions.roles import assign_role, clear_roles

class Command(BaseCommand):
    help = 'Atualiza as roles de todos os usuários com base no tipo_usuario.'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        total = 0
        atualizados = 0

        for user in User.objects.all():
            total += 1
            # Limpa roles atuais
            clear_roles(user)

            if user.tipo_usuario == 'A':
                assign_role(user, 'administrador')
                atualizados += 1
            elif user.tipo_usuario == 'C':
                assign_role(user, 'corretor')
                atualizados += 1
            elif user.tipo_usuario == 'P':
                assign_role(user, 'proprietario')
                atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Atualização concluída. {atualizados}/{total} usuários receberam roles.'
        ))
