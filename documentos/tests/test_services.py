"""Testes da renderização segura e validação de modelos (Fase 11)."""
from django.test import TestCase

from documentos import services


class RenderizacaoSeguraTest(TestCase):
	def test_renderiza_variavel_valida(self):
		html = services.renderizar_variaveis(
			'Cliente: {{ cliente.nome }}', {'cliente': {'nome': 'JOÃO'}}
		)
		self.assertEqual(html, 'Cliente: JOÃO')

	def test_variavel_invalida_vira_placeholder(self):
		html = services.renderizar_variaveis('{{ inexistente }}', {})
		self.assertIn('VARIÁVEL INVÁLIDA', html)

	def test_valor_com_html_e_escapado(self):
		# Segurança: HTML vindo de valor de variável é escapado (anti-injeção).
		# A estrutura HTML do template passa intacta; só os valores são escapados.
		html = services.renderizar_variaveis(
			'<p>{{ a }}</p>', {'a': '<script>x</script>'}
		)
		self.assertEqual(html, '<p>&lt;script&gt;x&lt;/script&gt;</p>')


class ValidacaoModeloTest(TestCase):
	"""As 48 VariavelDocumento vêm da data migration 0007 no test DB."""

	def test_aceita_variavel_existente(self):
		erros = services.validar_conteudo_modelo('{{ cliente.nome }}')
		self.assertEqual(erros, [])

	def test_bloqueia_tag_de_template(self):
		erros = services.validar_conteudo_modelo('{% if x %}{% endif %}')
		self.assertTrue(any('Tags de template' in e for e in erros))

	def test_rejeita_variavel_inexistente(self):
		erros = services.validar_conteudo_modelo('{{ cliente.inexistente }}')
		self.assertTrue(any('inválidas' in e for e in erros))
		self.assertTrue(any('cliente.inexistente' in e for e in erros))

	def test_multiplas_variaveis_validas(self):
		conteudo = '{{ cliente.nome }} {{ venda.valor_total }} {{ sistema.data_hoje }}'
		self.assertEqual(services.validar_conteudo_modelo(conteudo), [])


class ExtensoInteiroFemininoTest(TestCase):
	"""Conversão de inteiro para extenso feminino (usado em qtd_parcelas_extenso)."""

	def _f(self, n):
		return services._extenso_inteiro_feminino(n)

	def test_1_retorna_uma(self):
		self.assertEqual(self._f(1), 'uma')

	def test_2_retorna_duas(self):
		self.assertEqual(self._f(2), 'duas')

	def test_12_retorna_doze(self):
		self.assertEqual(self._f(12), 'doze')

	def test_21_retorna_vinte_e_uma(self):
		self.assertEqual(self._f(21), 'vinte e uma')

	def test_100_retorna_cem(self):
		self.assertEqual(self._f(100), 'cem')

	def test_0_retorna_zero(self):
		self.assertEqual(self._f(0), 'zero')

	def test_none_retorna_vazio(self):
		self.assertEqual(self._f(None), '')
