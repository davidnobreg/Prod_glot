"""Testes de numeração, imutabilidade e versionamento (Fase 11)."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from documentos.models import (
	DocumentoGerado,
	ModeloDocumento,
	ModeloDocumentoHistorico,
	SequencialDocumento,
	StatusDocumento,
)


def _criar_usuario():
	User = get_user_model()
	return User.objects.create_user(username='tester', password='x123456')


class SequencialTest(TestCase):
	def test_gera_sequencia_com_prefixo_e_ano(self):
		with transaction.atomic():
			n1 = SequencialDocumento.proximo_numero('contrato')
			n2 = SequencialDocumento.proximo_numero('contrato')
		self.assertTrue(n1.startswith('CTR-'))
		self.assertTrue(n1.endswith('-0001'))
		self.assertTrue(n2.endswith('-0002'))

	def test_prefixos_distintos_por_tipo(self):
		with transaction.atomic():
			contrato = SequencialDocumento.proximo_numero('contrato')
			distrato = SequencialDocumento.proximo_numero('distrato')
		self.assertTrue(contrato.startswith('CTR-'))
		self.assertTrue(distrato.startswith('DST-'))
		self.assertTrue(distrato.endswith('-0001'))  # sequência independente


class ModeloVersaoTest(TestCase):
	def setUp(self):
		self.user = _criar_usuario()

	def test_mudanca_de_conteudo_incrementa_versao_e_arquiva(self):
		modelo = ModeloDocumento.objects.create(
			titulo='M', tipo='contrato', conteudo_html='<p>v1</p>', criado_por=self.user,
		)
		self.assertEqual(modelo.versao, 1)

		modelo.conteudo_html = '<p>v2</p>'
		modelo._editado_por = self.user
		modelo.save()

		modelo.refresh_from_db()
		self.assertEqual(modelo.versao, 2)
		hist = ModeloDocumentoHistorico.objects.filter(modelo=modelo)
		self.assertEqual(hist.count(), 1)
		self.assertEqual(hist.first().conteudo_html, '<p>v1</p>')  # arquiva o ANTERIOR

	def test_save_sem_mudanca_de_conteudo_nao_versiona(self):
		modelo = ModeloDocumento.objects.create(
			titulo='M', tipo='contrato', conteudo_html='<p>x</p>', criado_por=self.user,
		)
		modelo.titulo = 'Outro título'
		modelo.save()
		modelo.refresh_from_db()
		self.assertEqual(modelo.versao, 1)
		self.assertEqual(ModeloDocumentoHistorico.objects.count(), 0)


class ImutabilidadeTest(TestCase):
	def setUp(self):
		self.user = _criar_usuario()
		self.modelo = ModeloDocumento.objects.create(
			titulo='M', tipo='contrato', conteudo_html='<p>x</p>', criado_por=self.user,
		)

	def test_documento_finalizado_bloqueia_alteracao_de_conteudo(self):
		doc = DocumentoGerado.objects.create(
			modelo=self.modelo, modelo_versao_snapshot=1,
			titulo='Doc', conteudo_final_html='<p>final</p>',
			status=StatusDocumento.FINALIZADO, criado_por=self.user,
		)
		doc.conteudo_final_html = '<p>alterado</p>'
		with self.assertRaises(ValidationError):
			doc.save()

	def test_rascunho_pode_ser_alterado(self):
		doc = DocumentoGerado.objects.create(
			modelo=self.modelo, modelo_versao_snapshot=1,
			titulo='Doc', conteudo_final_html='<p>rascunho</p>',
			status=StatusDocumento.RASCUNHO, criado_por=self.user,
		)
		doc.conteudo_final_html = '<p>editado</p>'
		doc.save()  # não deve levantar
		doc.refresh_from_db()
		self.assertEqual(doc.conteudo_final_html, '<p>editado</p>')

	def test_numero_gerado_automaticamente_na_criacao(self):
		doc = DocumentoGerado.objects.create(
			modelo=self.modelo, modelo_versao_snapshot=1,
			titulo='Doc', conteudo_final_html='<p>x</p>',
			status=StatusDocumento.RASCUNHO, criado_por=self.user,
		)
		self.assertTrue(doc.numero.startswith('CTR-'))
