from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class Command(BaseCommand):
	help = 'Registra tasks periódicas no Celery Beat'

	def handle(self, *args, **kwargs):
		schedule_1min, _ = IntervalSchedule.objects.get_or_create(
			every=1,
			period=IntervalSchedule.MINUTES,
		)

		task, created = PeriodicTask.objects.get_or_create(
			name='LIBERAR_LOTES_SEM_VENDA',
			defaults={
				'task': 'empreendimentos.tasks.liberar_lotes_sem_venda',
				'interval': schedule_1min,
				'enabled': True,
			}
		)

		if created:
			self.stdout.write(self.style.SUCCESS('Task LIBERAR_LOTES_SEM_VENDA registrada'))
		else:
			self.stdout.write('Task LIBERAR_LOTES_SEM_VENDA já existe')
