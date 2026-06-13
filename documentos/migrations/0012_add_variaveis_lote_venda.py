from django.db import migrations


NOVAS_VARIAVEIS = [
	('lote', 'lote.medidas', 'Medidas do lote', '8,29x23,71x8,00x21,80', 10),
	('lote', 'lote.confrontacoes', 'Confrontações', 'Norte: Rua Projetada 01...', 11),
	('venda', 'venda.valor_sinal', 'Valor do sinal (R$)', 'R$ 3.000,00', 20),
	('venda', 'venda.valor_sinal_extenso', 'Sinal por extenso', 'três mil reais', 21),
	('venda', 'venda.data_primeira_parcela', 'Data da 1ª parcela', '10/02/2026', 22),
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
		("documentos", "0011_add_status_erro_documento"),
	]

	operations = [
		migrations.RunPython(criar_variaveis, remover_variaveis),
	]
