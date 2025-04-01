from django.apps import AppConfig

class VendasConfig(AppConfig):
    name = 'vendas'

    def ready(self):
        # Garantir que a tarefa periódica esteja registrada
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        from datetime import timedelta
        import json

        # Criar o intervalo de 5 minutos, se ainda não existir
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )

        # Criar a tarefa agendada, se ela não existir
        PeriodicTask.objects.get_or_create(
            interval=schedule,
            name="Liberar Lotes Reservados Expirados",
            task="vendas.tasks.liberar_lotes_reservados_expirados",
            defaults={"args": json.dumps([])},
        )
