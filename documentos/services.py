import hashlib
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.template import Context, Engine
from django.utils import timezone
from babel.dates import format_date
from num2words import num2words


def formatar_moeda_br(valor):
	try:
		return (
			f"R$ {float(valor):,.2f}"
			.replace(",", "X")
			.replace(".", ",")
			.replace("X", ".")
		)
	except (TypeError, ValueError):
		return "R$ 0,00"


def _para_float(valor):
	try:
		return float(valor or 0)
	except (TypeError, ValueError, AttributeError):
		return 0.0


def _para_int(valor):
	try:
		return int(valor or 0)
	except (TypeError, ValueError, AttributeError):
		return 0


def construir_contexto_venda(venda, contato_cliente):
	"""Monta o contexto completo usado nos documentos de proposta/contrato.

	Centraliza os cálculos que antes estavam duplicados em proposta(),
	propostaRascunho() e proposta_pdf().
	"""
	empreendimento = venda.lote.quadra.empr

	data_por_extenso = format_date(
		timezone.now().date(),
		format="d 'de' MMMM 'de' y",
		locale='pt_BR'
	)

	# ======================
	# VALORES
	# ======================
	area = _para_float(venda.lote.area)
	valor_metro = _para_float(venda.lote.valor_metro_quadrado)
	valor_total = area * valor_metro

	correcao = _para_float(getattr(empreendimento, 'correcao', 0))
	valor_corrigido = valor_total + (valor_total * (correcao / 100))

	sinal = _para_float(venda.valor_sinal)
	entrada = _para_float(venda.valor_entrada)
	valor_desconto = _para_float(venda.valor_desconto)
	valor_parcela = _para_float(venda.valor_parcela)
	valor_financiado = valor_corrigido - entrada - valor_desconto

	total_parcelas = _para_int(venda.quantidade_parcelas)

	# ======================
	# SINAL POR EXTENSO
	# ======================
	try:
		valor_extenso = num2words(
			sinal, lang='pt_BR', to='currency'
		).upper()
	except (TypeError, ValueError):
		valor_extenso = ''

	# ======================
	# REAJUSTE
	# ======================
	if venda.reajuste:
		tipo_reajuste = empreendimento.tipo_correcao or 'IGPM'
		frase_reajuste = f"AS PARCELAS SERÃO CORRIGIDAS PELO {tipo_reajuste}."
	else:
		frase_reajuste = "AS PARCELAS SERÃO FIXAS."

	return {
		# objetos
		'venda': venda,
		'endereco_cliente': venda.cliente,
		'contato_cliente': contato_cliente,
		'conjuge': venda.cliente,
		# datas
		'data_por_extenso': data_por_extenso,
		'data_primeira_parcela': venda.dt_primeira_parcela,
		# valores formatados
		'valor_total_formatado': formatar_moeda_br(valor_total),
		'valor_entrada_formatado': formatar_moeda_br(entrada),
		'valor_sinal_formatado': formatar_moeda_br(sinal),
		'valor_desconto_formatado': formatar_moeda_br(valor_desconto),
		'valor_parcela_formatado': formatar_moeda_br(valor_parcela),
		'valor_financiado_formatado': formatar_moeda_br(valor_financiado),
		'valor_corrigido_formatado': formatar_moeda_br(valor_corrigido),
		'valor_extenso': valor_extenso,
		# parcelas / correção
		'total_parcelas': total_parcelas,
		'qtd_parcelas_extenso': _extenso_inteiro_feminino(total_parcelas),
		'valor_parcela_extenso': _extenso_moeda(valor_parcela),
		'correcao': correcao,
		'frase_reajuste': frase_reajuste,
		# observação
		'observacao': venda.observacao,
	}


# ==========================================================
# MÓDULO DE DOCUMENTOS (Fase 4) — contexto aninhado p/ variáveis globais
# Entrega valores prontos (strings formatadas), nunca objetos do ORM.
# ==========================================================

def _so_digitos(valor):
	return re.sub(r'\D', '', valor or '')


def _formatar_cpf_cnpj(valor):
	d = _so_digitos(valor)
	if len(d) == 11:
		return f'{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}'
	if len(d) == 14:
		return f'{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}'
	return valor or ''


def _extenso_moeda(valor):
	try:
		return num2words(_para_float(valor), lang='pt_BR', to='currency')
	except (TypeError, ValueError):
		return ''


def _extenso_inteiro_feminino(n):
	"""Converte inteiro para extenso em português, gênero feminino.

	num2words gera masculino por padrão (um, dois, duzentos).
	Aplica substituições para concordar com 'parcela' (feminino):
	  1 → 'uma', 2 → 'duas', 21 → 'vinte e uma', 201 → 'duzentas e uma'.
	"""
	try:
		texto = num2words(int(n), lang='pt_BR')
		texto = re.sub(r'\bduzentos\b', 'duzentas', texto)
		texto = re.sub(r'\bdois\b', 'duas', texto)
		texto = re.sub(r'\bum\b', 'uma', texto)
		return texto
	except (TypeError, ValueError):
		return ''


def _data_br(d):
	return d.strftime('%d/%m/%Y') if d else ''


def _data_extenso(d):
	if not d:
		return ''
	return format_date(d, format="d 'de' MMMM 'de' y", locale='pt_BR')


def _endereco_completo(c):
	partes = [
		', '.join(p for p in [c.end_rua, c.end_numero] if p),
		c.end_bairro,
		'/'.join(p for p in [c.end_cidade, c.end_estado] if p),
	]
	texto = ', '.join(p for p in partes if p)
	if c.end_cep:
		texto = f'{texto}, CEP {c.end_cep}' if texto else f'CEP {c.end_cep}'
	return texto


def montar_contexto_venda(venda, usuario):
	"""Contexto aninhado (dict de dicts) com TODAS as chaves da Fase 3.

	Campos de cônjuge/inexistentes retornam '' (nunca quebra).
	"""
	cliente = venda.cliente
	lote = venda.lote
	quadra = lote.quadra if lote else None
	empr = quadra.empr if quadra else None
	hoje = timezone.now().date()

	telefone = cliente.telefones.filter(is_ativo=True).first() if cliente else None

	area = _para_float(lote.area) if lote else 0
	valor_metro = _para_float(lote.valor_metro_quadrado) if lote else 0
	valor_lote = area * valor_metro
	entrada = _para_float(venda.valor_entrada)
	parcela = _para_float(venda.valor_parcela)
	qtd_parcelas = _para_int(venda.quantidade_parcelas)

	return {
		'cliente': {
			'nome': cliente.name if cliente else '',
			'cpf': _so_digitos(cliente.documento) if cliente else '',
			'cpf_formatado': _formatar_cpf_cnpj(cliente.documento) if cliente else '',
			'rg': cliente.numero_rg if cliente else '',
			'estado_civil': cliente.get_estado_civil_display() if cliente else '',
			'profissao': cliente.profissao if cliente else '',
			'nacionalidade': cliente.nacionalidade if cliente else '',
			'naturalidade': cliente.naturalidade if cliente else '',
			'endereco_completo': _endereco_completo(cliente) if cliente else '',
			'telefone': telefone.numero if telefone else '',
			'email': cliente.email if cliente else '',
		},
		'conjuge': {
			'nome': cliente.conj_nome or '' if cliente else '',
			'cpf_formatado': _formatar_cpf_cnpj(cliente.conj_documento) if cliente else '',
			'rg': cliente.conj_numero_rg or '' if cliente else '',
			'profissao': cliente.conj_profissao or '' if cliente else '',
			'nacionalidade': cliente.conj_nacionalidade or '' if cliente else '',
		},
		'empreendimento': {
			'nome': empr.nome if empr else '',
			'razao_social': empr.razaoSocial if empr else '',
			'cnpj_formatado': _formatar_cpf_cnpj(empr.cnpj) if empr else '',
			'matricula': empr.matricula if empr else '',
			'endereco': ', '.join(p for p in [empr.rua, empr.numero] if p) if empr else '',
			'cidade': empr.cidade if empr else '',
			'estado': empr.estado if empr else '',
			'representante_nome': empr.representante_nome if empr else '',
			'representante_cpf': _formatar_cpf_cnpj(empr.representante_cpf) if empr else '',
			'representante_rg': empr.representante_rg if empr else '',
			'cidade_foro': empr.cidade_foro or (empr.cidade if empr else ''),
		},
		'quadra': {
			'nome': quadra.namequadra if quadra else '',
		},
		'lote': {
			'numero': lote.lote if lote else '',
			'area_formatada': f'{area:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
			'valor_formatado': formatar_moeda_br(valor_lote),
			'medidas': lote.medidas if lote else '',
			'confrontacoes': lote.confrontacoes if lote else '',
		},
		'venda': {
			'numero': str(venda.id),
			'valor_total': formatar_moeda_br(valor_lote),
			'valor_total_extenso': _extenso_moeda(valor_lote),
			'valor_entrada': formatar_moeda_br(entrada),
			'valor_entrada_extenso': _extenso_moeda(entrada),
			'qtd_parcelas': str(qtd_parcelas),
			'qtd_parcelas_extenso': _extenso_inteiro_feminino(qtd_parcelas),
			'valor_parcela': formatar_moeda_br(parcela),
			'valor_parcela_extenso': _extenso_moeda(parcela),
			'data_venda': _data_br(venda.dt_venda),
			'data_venda_extenso': _data_extenso(venda.dt_venda),
			'forma_pagamento': 'Parcelado' if qtd_parcelas > 1 else 'À vista',
			'valor_sinal': formatar_moeda_br(_para_float(venda.valor_sinal)) if venda else '',
			'valor_sinal_extenso': _extenso_moeda(venda.valor_sinal) if venda else '',
			'data_primeira_parcela': _data_br(venda.dt_primeira_parcela) if venda else '',
			'corretor_nome': venda.corretor_nome if venda else '',
		},
		'sistema': {
			'data_hoje': _data_br(hoje),
			'data_hoje_extenso': _data_extenso(hoje),
			'cidade_estado': '/'.join(p for p in [empr.cidade, empr.estado] if p) if empr else '',
		},
		'usuario': {
			'nome': (usuario.get_full_name() or usuario.get_username()) if usuario else '',
		},
	}


def montar_contexto_distrato(distrato, usuario):
	"""Contexto da venda + chaves distrato.*"""
	contexto = montar_contexto_venda(distrato.venda, usuario)
	contexto['distrato'] = {
		'motivo': distrato.motivo,
		'data_distrato': _data_br(distrato.data_distrato),
		'data_extenso': _data_extenso(distrato.data_distrato),
		'valor_devolucao': formatar_moeda_br(distrato.valor_devolucao),
		'valor_extenso': _extenso_moeda(distrato.valor_devolucao),
		'percentual_retencao': str(distrato.percentual_retencao),
	}
	return contexto


# ----------------------------------------------------------
# Renderização segura
# ----------------------------------------------------------
_engine_seguro = Engine(
	debug=False,
	libraries={},
	builtins=['django.template.defaulttags'],
	string_if_invalid='[VARIÁVEL INVÁLIDA: %s]',
	autoescape=False,
)


def renderizar_variaveis(conteudo_html, contexto):
	template = _engine_seguro.from_string(conteudo_html)
	return template.render(Context(contexto))


# ----------------------------------------------------------
# Validação de variáveis (antes de salvar modelo)
# ----------------------------------------------------------
RE_VARIAVEL = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
RE_TAG_PROIBIDA = re.compile(r'\{%')


def validar_conteudo_modelo(conteudo_html):
	"""Retorna lista de erros. Vazia = OK."""
	from .models import VariavelDocumento

	erros = []
	if RE_TAG_PROIBIDA.search(conteudo_html):
		erros.append('Tags de template ({% %}) não são permitidas.')
	usadas = set(RE_VARIAVEL.findall(conteudo_html))
	permitidas = set(
		VariavelDocumento.objects.filter(ativo=True).values_list('tag_slug', flat=True)
	)
	invalidas = usadas - permitidas
	if invalidas:
		erros.append(f'Variáveis inválidas: {", ".join(sorted(invalidas))}')
	return erros


# ----------------------------------------------------------
# Geração de documento
# ----------------------------------------------------------
def gerar_documento_venda(venda, tipo, usuario, modelo_id=None, substitui_id=None):
	"""Cria DocumentoGerado (RASCUNHO) para uma venda."""
	from .models import DocumentoGerado, ModeloDocumento, StatusDocumento

	empreendimento = venda.lote.quadra.empr

	with transaction.atomic():
		if modelo_id:
			modelo = ModeloDocumento.objects.get(pk=modelo_id)
			disponivel = ModeloDocumento.objects.para_empreendimento(
				empreendimento
			).filter(pk=modelo.pk).exists()
			if not disponivel:
				raise ValidationError('Modelo não disponível para este empreendimento.')
		else:
			modelo = ModeloDocumento.objects.padrao_para(empreendimento, tipo)
			if not modelo:
				raise ValidationError(
					f'Nenhum modelo padrão de {tipo} configurado para {empreendimento}.'
				)

		contexto = montar_contexto_venda(venda, usuario)
		html_final = renderizar_variaveis(modelo.conteudo_html, contexto)

		doc = DocumentoGerado(
			modelo=modelo,
			modelo_versao_snapshot=modelo.versao,
			venda=venda,
			cliente=venda.cliente,
			titulo=f'{modelo.titulo} — {venda.cliente}',
			conteudo_final_html=html_final,
			status=StatusDocumento.RASCUNHO,
			criado_por=usuario,
		)
		doc.save()  # numero gerado no save()

		if substitui_id:
			anterior = DocumentoGerado.objects.select_for_update().get(pk=substitui_id)
			anterior.status = StatusDocumento.SUBSTITUIDO
			anterior.save(update_fields=['status'])
			doc.substitui = anterior
			doc.save(update_fields=['substitui'])

	return doc


def finalizar_documento(doc, usuario):
	"""Marca PROCESSANDO, calcula hash e dispara a task de PDF."""
	from .models import StatusDocumento
	from .tasks import gerar_pdf_documento

	if doc.status != StatusDocumento.RASCUNHO:
		raise ValidationError('Apenas rascunhos podem ser finalizados.')
	doc.status = StatusDocumento.PROCESSANDO
	doc.hash_conteudo = hashlib.sha256(doc.conteudo_final_html.encode()).hexdigest()
	doc.save(update_fields=['status', 'hash_conteudo'])
	gerar_pdf_documento.delay(doc.pk)
	return doc


# ----------------------------------------------------------
# Duplicar modelo
# ----------------------------------------------------------
def duplicar_modelo(modelo, usuario):
	"""Cópia com versao=1; vínculos copiados com padrao=False, ativo=False."""
	from .models import EmpreendimentoDocumento, ModeloDocumento

	with transaction.atomic():
		copia = ModeloDocumento.objects.create(
			titulo=f'{modelo.titulo} (cópia)',
			tipo=modelo.tipo,
			conteudo_html=modelo.conteudo_html,
			eh_global=modelo.eh_global,
			versao=1,
			ativo=modelo.ativo,
			criado_por=usuario,
		)
		vinculos = EmpreendimentoDocumento.objects.filter(modelo=modelo)
		for v in vinculos:
			EmpreendimentoDocumento.objects.create(
				empreendimento=v.empreendimento,
				modelo=copia,
				padrao=False,
				ativo=False,
				ordem=v.ordem,
			)
	return copia


# ----------------------------------------------------------
# Margem de página por empreendimento (régua do editor)
# ----------------------------------------------------------
def atualizar_margens_documento(empreendimento, margem_sup, margem_dir, margem_inf, margem_esq):
	"""Atualiza (ou cria) a ConfiguracaoDocumento do empreendimento com novas
	margens de página, em mm. Retorna lista de erros; vazia = salvou OK."""
	from .models import ConfiguracaoDocumento

	valores = {
		'margem_sup': margem_sup, 'margem_dir': margem_dir,
		'margem_inf': margem_inf, 'margem_esq': margem_esq,
	}
	erros = []
	for nome, valor in valores.items():
		if not isinstance(valor, int) or isinstance(valor, bool) or valor < 5 or valor > 100:
			erros.append(f'{nome} deve ser um inteiro entre 5 e 100 (mm).')
	if erros:
		return erros

	cfg, _ = ConfiguracaoDocumento.objects.get_or_create(empreendimento=empreendimento)
	cfg.margem_sup = margem_sup
	cfg.margem_dir = margem_dir
	cfg.margem_inf = margem_inf
	cfg.margem_esq = margem_esq
	cfg.save(update_fields=['margem_sup', 'margem_dir', 'margem_inf', 'margem_esq'])
	return []
