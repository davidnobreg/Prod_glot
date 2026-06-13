from django.db import migrations


NOVAS_VARIAVEIS = [
	('empreendimento', 'empreendimento.representante_nome', 'Nome do representante', 'João Silva', 10),
	('empreendimento', 'empreendimento.representante_cpf', 'CPF do representante', '000.000.000-00', 11),
	('empreendimento', 'empreendimento.representante_rg', 'RG do representante', '0000000', 12),
	('empreendimento', 'empreendimento.matricula', 'Matrícula do imóvel', '2664', 13),
	('empreendimento', 'empreendimento.cidade_foro', 'Cidade do foro', 'Mauriti - CE', 14),
	('venda', 'venda.corretor_nome', 'Nome do corretor', 'Carlos Werneck', 23),
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
		("documentos", "0012_add_variaveis_lote_venda"),
	]

	operations = [
		migrations.RunPython(criar_variaveis, remover_variaveis),
	]
