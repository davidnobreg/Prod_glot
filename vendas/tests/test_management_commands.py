import pytest
from io import StringIO

from django.core.management import call_command

from vendas.models import VendaDocumento


@pytest.mark.django_db
def test_relatorio_lista_venda_em_risco_ambos_tipos(venda_pre_venda, admin_user):
	"""Sem --tipo, relatório cobre proposta_assinada E contrato_assinado."""
	VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='contrato_assinado', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/contrato.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', stdout=out)
	assert '2 VendaDocumento em risco' in out.getvalue()


@pytest.mark.django_db
def test_relatorio_filtra_por_tipo(venda_pre_venda, admin_user):
	"""Com --tipo contrato_assinado, ignora proposta_assinada em risco."""
	VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', '--tipo', 'contrato_assinado', stdout=out)
	assert '0 VendaDocumento em risco' in out.getvalue()


@pytest.mark.django_db
def test_relatorio_ignora_venda_inativa(venda, admin_user):
	"""Venda com is_ativo=False (mesmo em RESERVADO) não conta como risco."""
	venda.is_ativo = False
	venda.save(update_fields=['is_ativo'])
	VendaDocumento.objects.create(
		venda=venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/inativa.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', stdout=out)
	assert '0 VendaDocumento em risco' in out.getvalue()


@pytest.mark.django_db
def test_relatorio_ignora_venda_vendido(lote, cliente_pf, admin_user):
	"""tipo_venda fora de RESERVADO/PRE-VENDA (ex.: VENDIDO) não conta como risco."""
	from vendas.models import RegisterVenda
	venda_vendida = RegisterVenda.objects.create(
		lote=lote, cliente=cliente_pf, corretor=admin_user, tipo_venda='VENDIDO', is_ativo=True,
	)
	VendaDocumento.objects.create(
		venda=venda_vendida, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/vendida.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', stdout=out)
	assert '0 VendaDocumento em risco' in out.getvalue()


@pytest.mark.django_db
def test_relatorio_sem_auto_vincular_mostra_candidato_existente_sem_escrever(
	venda_pre_venda, admin_user,
):
	"""Regressão do bug real: modo relatório (sem --auto-vincular) tinha 'candidato'
	sempre None porque só era calculado dentro do if options['auto_vincular'] — reportava
	SEM CANDIDATO mesmo quando existia um DocumentoGerado FINALIZADO válido. O candidato
	precisa ser calculado sempre (é leitura); só a escrita fica atrás da flag."""
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', stdout=out)   # sem --auto-vincular
	saida = out.getvalue()

	assert 'SEM CANDIDATO' not in saida
	assert f'candidato encontrado: DocumentoGerado {doc_gerado.numero}' in saida
	assert 'com candidato disponível: 1' in saida
	assert 'sem candidato (decisão manual): 0' in saida

	doc.refresh_from_db()
	assert doc.documento_gerado_id is None   # relatório não escreve nada


@pytest.mark.django_db
def test_auto_vincular_encontra_documento_gerado_finalizado(venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	call_command('vincular_documentos_pendentes', '--auto-vincular', stdout=StringIO())
	doc.refresh_from_db()
	assert doc.documento_gerado_id == doc_gerado.id


@pytest.mark.django_db
def test_auto_vincular_funciona_para_contrato_assinado(venda_pre_venda, admin_user):
	"""Mesmo fluxo pro tipo contrato_assinado -> casa com modelo__tipo='contrato'.
	Usa o mesmo services.documento_gerado_mais_recente do upload (Etapa 1), não lógica nova."""
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato', tipo='contrato', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	doc_gerado = DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Contrato',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='contrato_assinado', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/contrato.pdf',
	)
	call_command('vincular_documentos_pendentes', '--auto-vincular', stdout=StringIO())
	doc.refresh_from_db()
	assert doc.documento_gerado_id == doc_gerado.id


@pytest.mark.django_db
def test_auto_vincular_sem_candidato_fica_pendente(venda_pre_venda, admin_user):
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	out = StringIO()
	call_command('vincular_documentos_pendentes', '--auto-vincular', stdout=out)
	doc.refresh_from_db()
	assert doc.documento_gerado_id is None
	assert 'pendentes de decisão manual: 1' in out.getvalue()


@pytest.mark.django_db
def test_dry_run_nao_salva(venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)
	doc = VendaDocumento.objects.create(
		venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
		enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
	)
	call_command('vincular_documentos_pendentes', '--auto-vincular', '--dry-run', stdout=StringIO())
	doc.refresh_from_db()
	assert doc.documento_gerado_id is None
