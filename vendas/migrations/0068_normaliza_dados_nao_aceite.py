from django.db import migrations


def normaliza_nao_aceite_para_underscore(apps, schema_editor):
	RegisterVenda = apps.get_model('vendas', 'RegisterVenda')
	RegisterVenda.objects.filter(tipo_venda='NAO-ACEITE').update(tipo_venda='NAO_ACEITE')


def reverte_para_hifen(apps, schema_editor):
	RegisterVenda = apps.get_model('vendas', 'RegisterVenda')
	RegisterVenda.objects.filter(tipo_venda='NAO_ACEITE').update(tipo_venda='NAO-ACEITE')


class Migration(migrations.Migration):

	dependencies = [
		("vendas", "0067_add_uuid_vendadocumento"),
	]

	operations = [
		migrations.RunPython(normaliza_nao_aceite_para_underscore, reverte_para_hifen),
	]
