"""Regressão: modal 'Gerar Documento' — gate de tipo por etapa do lote
e isolamento do dropdown 'Substituir documento existente' por venda."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from empreendimentos.models import Empreendimento, Quadra, Lote
from vendas.models import RegisterVenda
from documentos.models import DocumentoGerado, ModeloDocumento

User = get_user_model()


def _make_empreendimento():
	return Empreendimento.objects.create(
		nome='Residencial Teste',
		telefone='(83) 99999-9999',
		tempo_reserva=30,
		quantidade_parcela=60,
	)


def _make_quadra(empr):
	return Quadra.objects.create(namequadra='Quadra A', empr=empr)


def _make_lote(quadra, numero='Lote 01', situacao='ANALISE'):
	return Lote.objects.create(
		quadra=quadra,
		lote=numero,
		area='200',
		situacao=situacao,
		valor_metro_quadrado='1500.00',
		telefone='(83) 99999-9999',
		telefone_user='(83) 99999-9999',
		user='teste',
		cliente_reserva='0',
	)


class GerarDocumentoEtapaGateTest(TestCase):
	"""Bug 2: 'Tipo do documento' não pode oferecer Contrato enquanto o lote
	está em ANALISE — só libera a partir de RESERVADO."""

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.empr = _make_empreendimento()
		self.quadra = _make_quadra(self.empr)
		ModeloDocumento.objects.create(
			titulo='Proposta Padrão', tipo='proposta', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=self.user,
		)
		ModeloDocumento.objects.create(
			titulo='Contrato Padrão', tipo='contrato', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=self.user,
		)

	def test_analise_oferece_apenas_proposta(self):
		lote = _make_lote(self.quadra, situacao='ANALISE')
		venda = RegisterVenda.objects.create(lote=lote, tipo_venda='ANALISE')
		url = reverse('documentos:gerar-documento', args=[venda.pk])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('proposta', response.context['modelos_por_tipo'])
		self.assertNotIn('contrato', response.context['modelos_por_tipo'])

	def test_reservado_oferece_proposta_e_contrato(self):
		lote = _make_lote(self.quadra, situacao='RESERVADO')
		venda = RegisterVenda.objects.create(lote=lote, tipo_venda='RESERVADO')
		url = reverse('documentos:gerar-documento', args=[venda.pk])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('proposta', response.context['modelos_por_tipo'])
		self.assertIn('contrato', response.context['modelos_por_tipo'])

	def test_post_gerar_contrato_em_analise_bloqueado(self):
		lote = _make_lote(self.quadra, situacao='ANALISE')
		venda = RegisterVenda.objects.create(lote=lote, tipo_venda='ANALISE')
		url = reverse('documentos:gerar-documento', args=[venda.pk])
		response = self.client.post(url, {'tipo': 'contrato'})
		self.assertRedirects(response, url, fetch_redirect_response=False)
		self.assertFalse(DocumentoGerado.objects.filter(venda=venda, modelo__tipo='contrato').exists())


class GerarDocumentoIsolamentoTest(TestCase):
	"""Bug 1: dropdown 'Substituir documento existente' só pode listar
	documentos da venda/lote em contexto, nunca de outra venda."""

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_iso', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.empr = _make_empreendimento()
		self.quadra = _make_quadra(self.empr)
		self.modelo = ModeloDocumento.objects.create(
			titulo='Proposta Padrão', tipo='proposta', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=self.user,
		)

		self.lote_a = _make_lote(self.quadra, numero='Lote A', situacao='RESERVADO')
		self.venda_a = RegisterVenda.objects.create(lote=self.lote_a, tipo_venda='RESERVADO')
		self.doc_a = DocumentoGerado.objects.create(
			modelo=self.modelo, modelo_versao_snapshot=1, venda=self.venda_a,
			titulo='Proposta A', conteudo_final_html='<p>a</p>', criado_por=self.user,
		)

		self.lote_b = _make_lote(self.quadra, numero='Lote B', situacao='RESERVADO')
		self.venda_b = RegisterVenda.objects.create(lote=self.lote_b, tipo_venda='RESERVADO')
		self.doc_b = DocumentoGerado.objects.create(
			modelo=self.modelo, modelo_versao_snapshot=1, venda=self.venda_b,
			titulo='Proposta B', conteudo_final_html='<p>b</p>', criado_por=self.user,
		)

	def test_docs_existentes_isolado_por_venda(self):
		url = reverse('documentos:gerar-documento', args=[self.venda_a.pk])
		response = self.client.get(url)
		docs = list(response.context['docs_existentes'])
		self.assertIn(self.doc_a, docs)
		self.assertNotIn(self.doc_b, docs)
		self.assertContains(response, self.doc_a.numero)
		self.assertNotContains(response, self.doc_b.numero)