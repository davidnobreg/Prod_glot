from django.db import migrations


NOVAS_VARIAVEIS = [
	# conjuge
	('conjuge', 'conjuge.cpf', 'CPF do cônjuge (sem formatação)', '12345678900', 5),
	('conjuge', 'conjuge.estado_civil', 'Estado civil do cônjuge', 'Casado(a)', 6),
	('conjuge', 'conjuge.naturalidade', 'Naturalidade do cônjuge', 'São Paulo/SP', 7),
	('conjuge', 'conjuge.email', 'E-mail do cônjuge', 'conjuge@email.com', 8),
	('conjuge', 'conjuge.telefone', 'Telefone do cônjuge', '(88) 99999-9999', 9),

	# empreendimento
	('empreendimento', 'empreendimento.telefone', 'Telefone do empreendimento', '(88) 3333-3333', 15),
	('empreendimento', 'empreendimento.email', 'E-mail do empreendimento', 'contato@empreendimento.com.br', 16),
	('empreendimento', 'empreendimento.cep', 'CEP do empreendimento', '63180-000', 17),
	('empreendimento', 'empreendimento.representante_email', 'E-mail do representante legal', 'rep@empresa.com.br', 18),
	('empreendimento', 'empreendimento.representante_telefone', 'Telefone do representante legal', '(88) 99999-9999', 19),

	# transferencia
	('transferencia', 'transferencia.cedente_nome', 'Nome do cedente (quem transfere)', 'João da Silva', 0),
	('transferencia', 'transferencia.cedente_cpf_formatado', 'CPF do cedente', '123.456.789-00', 1),
	('transferencia', 'transferencia.cessionario_nome', 'Nome do cessionário (quem recebe)', 'Maria Souza', 2),
	('transferencia', 'transferencia.cessionario_cpf_formatado', 'CPF do cessionário', '987.654.321-00', 3),
	('transferencia', 'transferencia.data_transferencia', 'Data da transferência', '20/07/2026', 4),
	('transferencia', 'transferencia.data_transferencia_extenso', 'Data da transferência por extenso', '20 de julho de 2026', 5),

	# distrato
	('distrato', 'distrato.numero_contrato', 'Número do contrato distratado', '2024/001', 6),
]


def criar_variaveis(apps, schema_editor):
	VariavelDocumento = apps.get_model('documentos', 'VariavelDocumento')
	for categoria, tag_slug, label, exemplo, ordem in NOVAS_VARIAVEIS:
		VariavelDocumento.objects.get_or_create(
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
		("documentos", "0017_remove_distrato_scaffold_morto"),
	]

	operations = [
		migrations.RunPython(criar_variaveis, remover_variaveis),
	]
