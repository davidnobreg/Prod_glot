# empreendimentos/migrations/0099_remove_empreendimento_contrato_fk.py
#
# Opção B — Passo final: remove Empreendimento.contrato (FK → CadastroDocumento).
#
# PRÉ-REQUISITOS (execute nesta ordem antes de aplicar):
#   1. python manage.py migrate documentos 0010_migra_cadastro_para_modelo
#   2. Verificar que todos os Empreendimentos com contrato != NULL
#      têm EmpreendimentoDocumento vinculado:
#
#      python manage.py shell -c "
#      from empreendimentos.models import Empreendimento
#      from documentos.models import EmpreendimentoDocumento
#      sem_vinculo = [
#          e for e in Empreendimento.objects.filter(contrato__isnull=False)
#          if not EmpreendimentoDocumento.objects.filter(
#              empreendimento=e, modelo__tipo='contrato', padrao=True
#          ).exists()
#      ]
#      print('Sem vínculo:', sem_vinculo)
#      "
#
#   3. Somente se sem_vinculo == [] aplique esta migration.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('empreendimentos', '0056_alter_lote_situacao'),
        ('documentos', '0010_migra_cadastro_para_modelo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='empreendimento',
            name='contrato',
        ),
    ]
