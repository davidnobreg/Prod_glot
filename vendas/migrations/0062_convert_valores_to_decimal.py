from decimal import Decimal, InvalidOperation
from django.db import migrations, models


def normalize_char_to_decimal(apps, schema_editor):
	RegisterVenda = apps.get_model('vendas', 'RegisterVenda')
	fields = ['valor_sinal', 'valor_entrada', 'valor_parcela', 'valor_inicio_contrato']
	for venda in RegisterVenda.objects.all():
		for field in fields:
			val = getattr(venda, field)
			if val in (None, ''):
				setattr(venda, field, None)
			else:
				try:
					setattr(venda, field, str(Decimal(str(val).strip())))
				except InvalidOperation:
					setattr(venda, field, None)
		venda.save(update_fields=fields)


def reverse_decimal_to_char(apps, schema_editor):
	pass


class Migration(migrations.Migration):

	dependencies = [
		('vendas', '0061_rename_typelote_to_typevenda_add_pre_venda'),
	]

	operations = [
		migrations.RunPython(
			normalize_char_to_decimal,
			reverse_decimal_to_char,
		),
		migrations.AlterField(
			model_name='registervenda',
			name='valor_sinal',
			field=models.DecimalField(
				blank=True,
				decimal_places=2,
				default=Decimal('0.00'),
				max_digits=12,
				null=True,
				verbose_name='Valor do Sinal',
			),
		),
		migrations.AlterField(
			model_name='registervenda',
			name='valor_entrada',
			field=models.DecimalField(
				blank=True,
				decimal_places=2,
				default=Decimal('0.00'),
				max_digits=12,
				null=True,
				verbose_name='Valor do Entrada',
			),
		),
		migrations.AlterField(
			model_name='registervenda',
			name='valor_parcela',
			field=models.DecimalField(
				blank=True,
				decimal_places=2,
				default=Decimal('0.00'),
				max_digits=12,
				null=True,
				verbose_name='Valor da Parcela',
			),
		),
		migrations.AlterField(
			model_name='registervenda',
			name='valor_inicio_contrato',
			field=models.DecimalField(
				blank=True,
				decimal_places=2,
				default=Decimal('0.00'),
				max_digits=12,
				null=True,
				verbose_name='Valor do Contrato',
			),
		),
	]