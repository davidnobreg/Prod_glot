"""Seed dos 3 modelos globais iniciais (Fase 10).

Cria ModeloDocumento eh_global=True para contrato, proposta e distrato,
usando as variáveis globais do novo padrão ({{ cliente.nome }} etc).
Idempotente: usa update_or_create por (titulo, tipo).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from documentos.models import ModeloDocumento


CONTRATO_HTML = """
<h1>CONTRATO DE COMPRA E VENDA</h1>

<p><strong>VENDEDOR:</strong> {{ empreendimento.razao_social }}, inscrita no CNPJ
{{ empreendimento.cnpj_formatado }}, com sede em {{ empreendimento.endereco }},
{{ empreendimento.cidade }}/{{ empreendimento.estado }}.</p>

<p><strong>COMPRADOR:</strong> {{ cliente.nome }}, {{ cliente.nacionalidade }},
{{ cliente.estado_civil }}, {{ cliente.profissao }}, portador do RG {{ cliente.rg }}
e CPF {{ cliente.cpf_formatado }}, residente em {{ cliente.endereco_completo }},
telefone {{ cliente.telefone }}.</p>

<div class="clausula">
<p class="clausula-titulo">CLÁUSULA 1ª — DO OBJETO</p>
<p>O presente contrato tem por objeto o lote {{ lote.numero }}, {{ quadra.nome }},
do empreendimento {{ empreendimento.nome }}, com área de {{ lote.area_formatada }} m².</p>
</div>

<div class="clausula">
<p class="clausula-titulo">CLÁUSULA 2ª — DO PREÇO</p>
<p>O preço total ajustado é de {{ venda.valor_total }}
({{ venda.valor_total_extenso }}), com entrada de {{ venda.valor_entrada }}
({{ venda.valor_entrada_extenso }}) e o saldo em {{ venda.qtd_parcelas }} parcelas
de {{ venda.valor_parcela }} ({{ venda.valor_parcela_extenso }}).
Forma de pagamento: {{ venda.forma_pagamento }}.</p>
</div>

<p>{{ sistema.cidade_estado }}, {{ sistema.data_hoje_extenso }}.</p>

<div class="assinatura-bloco">
	<div class="assinatura-linha">{{ cliente.nome }}<br>Comprador</div>
	<div class="assinatura-linha">{{ empreendimento.razao_social }}<br>Vendedor</div>
</div>
""".strip()


PROPOSTA_HTML = """
<h1>PROPOSTA DE COMPRA E VENDA</h1>

<p><strong>PROPONENTE:</strong> {{ cliente.nome }}, {{ cliente.nacionalidade }},
{{ cliente.estado_civil }}, {{ cliente.profissao }}, CPF {{ cliente.cpf_formatado }},
RG {{ cliente.rg }}, residente em {{ cliente.endereco_completo }}.</p>

<p><strong>EMPREENDIMENTO:</strong> {{ empreendimento.nome }} —
{{ empreendimento.cidade }}/{{ empreendimento.estado }}.</p>

<div class="clausula">
<p>Proponho a aquisição do lote {{ lote.numero }}, {{ quadra.nome }},
área {{ lote.area_formatada }} m², pelo valor de {{ venda.valor_total }}
({{ venda.valor_total_extenso }}).</p>
<p>Entrada: {{ venda.valor_entrada }}. Parcelas: {{ venda.qtd_parcelas }} x
{{ venda.valor_parcela }}. Forma: {{ venda.forma_pagamento }}.</p>
</div>

<p>{{ sistema.cidade_estado }}, {{ sistema.data_hoje_extenso }}.</p>

<div class="assinatura-bloco">
	<div class="assinatura-linha">{{ cliente.nome }}<br>Proponente</div>
</div>
""".strip()


DISTRATO_HTML = """
<h1>TERMO DE DISTRATO</h1>

<p>Pelo presente instrumento, {{ empreendimento.razao_social }}, CNPJ
{{ empreendimento.cnpj_formatado }}, e {{ cliente.nome }}, CPF
{{ cliente.cpf_formatado }}, resolvem rescindir o contrato relativo ao lote
{{ lote.numero }}, {{ quadra.nome }}, do empreendimento {{ empreendimento.nome }}.</p>

<div class="clausula">
<p class="clausula-titulo">MOTIVO</p>
<p>{{ distrato.motivo }}</p>
</div>

<div class="clausula">
<p class="clausula-titulo">CONDIÇÕES</p>
<p>Fica ajustada a devolução de {{ distrato.valor_devolucao }}
({{ distrato.valor_extenso }}), com retenção de {{ distrato.percentual_retencao }}%
sobre os valores pagos. Data do distrato: {{ distrato.data_distrato }}.</p>
</div>

<p>{{ sistema.cidade_estado }}, {{ distrato.data_extenso }}.</p>

<div class="assinatura-bloco">
	<div class="assinatura-linha">{{ cliente.nome }}<br>Distratante</div>
	<div class="assinatura-linha">{{ empreendimento.razao_social }}<br>Distratada</div>
</div>
""".strip()


MODELOS = [
	('Contrato de Compra e Venda', 'contrato', CONTRATO_HTML),
	('Proposta de Compra e Venda', 'proposta', PROPOSTA_HTML),
	('Termo de Distrato', 'distrato', DISTRATO_HTML),
]


class Command(BaseCommand):
	help = 'Cria os 3 modelos globais iniciais de documento.'

	def handle(self, *args, **options):
		User = get_user_model()
		autor = User.objects.filter(is_superuser=True).order_by('id').first()
		if not autor:
			autor = User.objects.order_by('id').first()
		if not autor:
			self.stderr.write('Nenhum usuário no banco para usar como criado_por.')
			return

		for titulo, tipo, html in MODELOS:
			modelo, criado = ModeloDocumento.objects.update_or_create(
				titulo=titulo,
				tipo=tipo,
				defaults={
					'conteudo_html': html,
					'eh_global': True,
					'ativo': True,
					'criado_por': autor,
				},
			)
			status = 'criado' if criado else 'atualizado'
			self.stdout.write(f'{status}: {titulo} ({tipo})')

		self.stdout.write(self.style.SUCCESS('Seed concluído.'))
