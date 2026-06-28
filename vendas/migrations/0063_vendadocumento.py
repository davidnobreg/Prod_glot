from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('documentos', '0014_add_variavel_qtd_parcelas_extenso'),
		('vendas', '0062_convert_valores_to_decimal'),
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
	]

	operations = [
		migrations.CreateModel(
			name='VendaDocumento',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('tipo', models.CharField(
					choices=[
						('proposta_assinada', 'Proposta Assinada'),
						('contrato_assinado', 'Contrato Assinado'),
						('outros', 'Outros'),
					],
					default='outros',
					max_length=30,
				)),
				('arquivo_assinado', models.FileField(upload_to='vendas/documentos_assinados/')),
				('status', models.CharField(
					choices=[
						('enviado', 'Enviado'),
						('aprovado', 'Aprovado'),
						('rejeitado', 'Rejeitado'),
					],
					default='enviado',
					max_length=20,
				)),
				('observacao', models.TextField(blank=True)),
				('enviado_em', models.DateTimeField(auto_now_add=True)),
				('aprovado_em', models.DateTimeField(blank=True, null=True)),
				('aprovado_por', models.ForeignKey(
					blank=True,
					null=True,
					on_delete=django.db.models.deletion.SET_NULL,
					related_name='documentos_aprovados',
					to=settings.AUTH_USER_MODEL,
				)),
				('documento_gerado', models.ForeignKey(
					blank=True,
					null=True,
					on_delete=django.db.models.deletion.SET_NULL,
					to='documentos.documentogerado',
				)),
				('enviado_por', models.ForeignKey(
					null=True,
					on_delete=django.db.models.deletion.SET_NULL,
					related_name='documentos_enviados',
					to=settings.AUTH_USER_MODEL,
				)),
				('venda', models.ForeignKey(
					on_delete=django.db.models.deletion.CASCADE,
					related_name='documentos_assinados',
					to='vendas.registervenda',
				)),
			],
			options={
				'verbose_name': 'Documento de Venda',
				'verbose_name_plural': 'Documentos de Venda',
				'ordering': ['-enviado_em'],
			},
		),
	]
