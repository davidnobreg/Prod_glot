from django.db import migrations


NOVAS_VARIAVEIS = [
	('venda', 'venda.qtd_parcelas_extenso', 'Qtd. parcelas por extenso (feminino)', 'doze', 24),
]


def criar_variaveis(apps, schema_editor):
	VariavelDocumento = apps.get_model('documentos', 'VariavelDocumento')
	for categoria, tag_slug, label, exemplo, ordem in NOVAS_VARIAVEIS:
		VariavelDocumento.objects.update_or_create(
			tag_slug=tag_slug,
			defaults={
				'categoria': categoria,
				'label': label,
				'exemplo': exemplo,
				'ativo': True,
				'ordem': ordem,
			},
		)


def remover_variaveis(apps, schema_editor):
	VariavelDocumento = apps.get_model('documentos', 'VariavelDocumento')
	slugs = [v[1] for v in NOVAS_VARIAVEIS]
	VariavelDocumento.objects.filter(tag_slug__in=slugs).delete()


class Migration(migrations.Migration):

	dependencies = [
		("documentos", "0013_add_variaveis_fase2"),
	]

	operations = [
		migrations.RunPython(criar_variaveis, remover_variaveis),
	]
