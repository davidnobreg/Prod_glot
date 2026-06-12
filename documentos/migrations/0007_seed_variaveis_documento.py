# Data migration: popula VariavelDocumento com as variáveis globais (Fase 3).
# tag_slug deve casar EXATAMENTE com as chaves de montar_contexto_* (Fase 4).
from django.db import migrations


VARIAVEIS = [
	# (categoria, tag_slug, label, exemplo)
	('cliente', 'cliente.nome', 'Nome completo', 'João da Silva'),
	('cliente', 'cliente.cpf', 'CPF (sem formatação)', '12345678900'),
	('cliente', 'cliente.cpf_formatado', 'CPF formatado', '123.456.789-00'),
	('cliente', 'cliente.rg', 'RG', '2001234567'),
	('cliente', 'cliente.estado_civil', 'Estado civil', 'Casado'),
	('cliente', 'cliente.profissao', 'Profissão', 'Engenheiro'),
	('cliente', 'cliente.nacionalidade', 'Nacionalidade', 'Brasileiro'),
	('cliente', 'cliente.naturalidade', 'Naturalidade', 'Juazeiro do Norte/CE'),
	('cliente', 'cliente.endereco_completo', 'Endereço completo', 'Rua A, 123, Centro, Juazeiro do Norte/CE, CEP 63000-000'),
	('cliente', 'cliente.telefone', 'Telefone principal', '(88) 99999-0000'),
	('cliente', 'cliente.email', 'E-mail', 'joao@email.com'),

	('conjuge', 'conjuge.nome', 'Nome do cônjuge', 'Maria da Silva'),
	('conjuge', 'conjuge.cpf_formatado', 'CPF do cônjuge', '987.654.321-00'),
	('conjuge', 'conjuge.rg', 'RG do cônjuge', '2007654321'),
	('conjuge', 'conjuge.profissao', 'Profissão do cônjuge', 'Professora'),
	('conjuge', 'conjuge.nacionalidade', 'Nacionalidade do cônjuge', 'Brasileira'),

	('empreendimento', 'empreendimento.nome', 'Nome do empreendimento', 'Residencial das Flores'),
	('empreendimento', 'empreendimento.razao_social', 'Razão social', 'Flores Empreendimentos LTDA'),
	('empreendimento', 'empreendimento.cnpj_formatado', 'CNPJ formatado', '12.345.678/0001-99'),
	('empreendimento', 'empreendimento.matricula', 'Matrícula do imóvel', '45.678'),
	('empreendimento', 'empreendimento.endereco', 'Endereço', 'Av. Principal, s/n'),
	('empreendimento', 'empreendimento.cidade', 'Cidade', 'Juazeiro do Norte'),
	('empreendimento', 'empreendimento.estado', 'Estado (UF)', 'CE'),

	('lote', 'quadra.nome', 'Quadra', 'Quadra 05'),
	('lote', 'lote.numero', 'Número do lote', '12'),
	('lote', 'lote.area_formatada', 'Área (m²)', '250,00'),
	('lote', 'lote.valor_formatado', 'Valor do lote (R$)', 'R$ 45.000,00'),

	('venda', 'venda.numero', 'Código da venda', '2047'),
	('venda', 'venda.valor_total', 'Valor total (R$)', 'R$ 45.000,00'),
	('venda', 'venda.valor_total_extenso', 'Valor total por extenso', 'quarenta e cinco mil reais'),
	('venda', 'venda.valor_entrada', 'Valor de entrada', 'R$ 5.000,00'),
	('venda', 'venda.valor_entrada_extenso', 'Entrada por extenso', 'cinco mil reais'),
	('venda', 'venda.qtd_parcelas', 'Quantidade de parcelas', '120'),
	('venda', 'venda.valor_parcela', 'Valor da parcela', 'R$ 333,33'),
	('venda', 'venda.valor_parcela_extenso', 'Parcela por extenso', 'trezentos e trinta e três reais e trinta e três centavos'),
	('venda', 'venda.data_venda', 'Data da venda', '10/06/2026'),
	('venda', 'venda.data_venda_extenso', 'Data por extenso', '10 de junho de 2026'),
	('venda', 'venda.forma_pagamento', 'Forma de pagamento', 'Parcelado'),

	('distrato', 'distrato.motivo', 'Motivo do distrato', 'Inadimplência'),
	('distrato', 'distrato.data_distrato', 'Data do distrato', '10/06/2026'),
	('distrato', 'distrato.data_extenso', 'Data por extenso', '10 de junho de 2026'),
	('distrato', 'distrato.valor_devolucao', 'Valor de devolução', 'R$ 3.500,00'),
	('distrato', 'distrato.valor_extenso', 'Devolução por extenso', 'três mil e quinhentos reais'),
	('distrato', 'distrato.percentual_retencao', '% de retenção', '30'),

	('sistema', 'sistema.data_hoje', 'Data atual', '10/06/2026'),
	('sistema', 'sistema.data_hoje_extenso', 'Data atual por extenso', '10 de junho de 2026'),
	('sistema', 'sistema.cidade_estado', 'Cidade/UF do empreendimento', 'Juazeiro do Norte/CE'),
	('sistema', 'usuario.nome', 'Usuário que gerou', 'Ana Lima'),
]


def criar_variaveis(apps, schema_editor):
	VariavelDocumento = apps.get_model('documentos', 'VariavelDocumento')
	ordem_por_cat = {}
	for categoria, tag_slug, label, exemplo in VARIAVEIS:
		ordem = ordem_por_cat.get(categoria, 0)
		ordem_por_cat[categoria] = ordem + 1
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
	slugs = [v[1] for v in VARIAVEIS]
	VariavelDocumento.objects.filter(tag_slug__in=slugs).delete()


class Migration(migrations.Migration):

	dependencies = [
		('documentos', '0006_fase2_novos_models_modulo_documentos'),
	]

	operations = [
		migrations.RunPython(criar_variaveis, remover_variaveis),
	]
