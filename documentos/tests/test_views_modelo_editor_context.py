from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento

User = get_user_model()


class ModeloEditorEmpreendimentosContextTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_ctx_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.empr = Empreendimento.objects.create(
			nome='Loteamento Régua Teste', telefone='(83) 98888-8888',
			tempo_reserva=30, quantidade_parcela=60,
		)
		ConfiguracaoDocumento.objects.create(empreendimento=self.empr, margem_sup=33, margem_dir=22, margem_inf=22, margem_esq=44)
		self.modelo = ModeloDocumento.objects.create(
			titulo='Contrato Régua Teste', tipo=TipoDocumento.CONTRATO,
			conteudo_html='<p>Teste</p>', criado_por=self.user,
		)
		EmpreendimentoDocumento.objects.create(empreendimento=self.empr, modelo=self.modelo)

	def test_editor_lista_empreendimento_vinculado_com_margens(self):
		url = reverse('documentos:modelo-editor', args=[self.modelo.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'Loteamento Régua Teste')
		self.assertContains(resp, str(self.empr.pk))
		self.assertContains(resp, '33')
		self.assertContains(resp, '44')

	def test_editor_sem_vinculo_lista_vazia(self):
		modelo_sem_vinculo = ModeloDocumento.objects.create(
			titulo='Proposta Sem Vínculo', tipo=TipoDocumento.PROPOSTA,
			conteudo_html='<p>x</p>', criado_por=self.user,
		)
		url = reverse('documentos:modelo-editor', args=[modelo_sem_vinculo.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.context['empreendimentos_vinculo'], [])


class ModeloEditorFontesContextTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_fontes_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.modelo = ModeloDocumento.objects.create(
			titulo='Contrato Fontes Teste', tipo=TipoDocumento.CONTRATO,
			conteudo_html='<p>Teste</p>', criado_por=self.user,
		)

	def test_editor_lista_fontes_e_tamanhos_fixos(self):
		url = reverse('documentos:modelo-editor', args=[self.modelo.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(
			[valor for valor, _rotulo in resp.context['fontes_familia']],
			['DejaVu Serif', 'DejaVu Sans', 'DejaVu Mono', 'Liberation Serif', 'Liberation Sans', 'Liberation Mono'],
		)
		self.assertEqual(resp.context['fontes_tamanho'], [9, 10, 11, 12, 14, 16, 18, 20, 24])
		self.assertContains(resp, 'DejaVu Serif')
		self.assertContains(resp, '24pt')