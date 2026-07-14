"""Lógica de negócio do wizard de cadastro de Empreendimento que não cabe em
model nem em view — mesmo padrão de `clientes/services.py`.
"""

from django.core.exceptions import ValidationError

from base.models import Endereco

from .models import RepresentanteLegal, DocumentoEmpreendimento, DocumentoRepresentante


def criar_ou_atualizar_endereco(dados, endereco=None):
	"""Cria um Endereco novo a partir de `dados` (cleaned_data de EnderecoForm).

	Cada entidade (empresa, empreendimento, representante) tem sua própria
	instância de Endereco — edição independente, nunca reutiliza instância
	existente de outra entidade. Se `endereco` for passado, atualiza os
	campos nele mesmo (edição do endereço já vinculado), em vez de criar um
	novo registro.
	"""
	if endereco is not None:
		for campo, valor in dados.items():
			setattr(endereco, campo, valor)
		endereco.full_clean()
		endereco.save()
		return endereco

	novo = Endereco(**dados)
	novo.full_clean()
	novo.save()
	return novo


def criar_representante(empreendimento, dados, endereco_dados=None):
	"""Cria RepresentanteLegal vinculado a `empreendimento`. `dados` já
	validado (cleaned_data de RepresentanteForm). Lança ValidationError
	(via full_clean) em duplicata de (empreendimento, documento).
	"""
	endereco = criar_ou_atualizar_endereco(endereco_dados) if endereco_dados else None

	representante = RepresentanteLegal(empreendimento=empreendimento, endereco=endereco, **dados)
	representante.full_clean()
	representante.save()
	return representante


def atualizar_representante(representante, dados, endereco_dados=None):
	"""Atualiza campos de `representante` com `dados`. Se `endereco_dados`
	for passado, atualiza (ou cria, se ainda não existir) o Endereco do
	próprio representante — nunca troca pra instância de outra entidade.
	"""
	for campo, valor in dados.items():
		setattr(representante, campo, valor)

	if endereco_dados:
		representante.endereco = criar_ou_atualizar_endereco(endereco_dados, endereco=representante.endereco)

	representante.full_clean()
	representante.save()
	return representante


def desativar_representante(representante):
	"""Soft delete — histórico (documento/contrato) pode referenciar o
	representante mesmo depois de removido do front do wizard."""
	representante.is_ativo = False
	representante.save(update_fields=['is_ativo'])


def criar_documento_empreendimento(empreendimento, categoria, arquivo, nome='', usuario=None):
	documento = DocumentoEmpreendimento(
		empreendimento=empreendimento, categoria=categoria, nome=nome,
		arquivo=arquivo, criado_por=usuario,
	)
	documento.full_clean()
	documento.save()
	return documento


def remover_documento_empreendimento(documento):
	documento.arquivo.delete(save=False)
	documento.delete()


def criar_documento_representante(representante, categoria, arquivo, nome='', usuario=None):
	"""Categorias de cônjuge só podem ser anexadas se o representante for
	casado — mesma regra exposta na UI (select filtrado por JS), mas
	revalidada aqui pra não depender só do client-side."""
	if categoria in DocumentoRepresentante.CATEGORIAS_CONJUGE and representante.estado_civil != 'casado':
		raise ValidationError('Categoria de cônjuge só é válida para representante casado(a).')

	documento = DocumentoRepresentante(
		representante=representante, categoria=categoria, nome=nome,
		arquivo=arquivo, criado_por=usuario,
	)
	documento.full_clean()
	documento.save()
	return documento


def remover_documento_representante(documento):
	documento.arquivo.delete(save=False)
	documento.delete()


CAMPOS_ENDERECO = ('cep', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'estado')


def sincronizar_endereco(endereco_destino, endereco_origem):
	"""Copia os campos de `endereco_origem` pra dentro de `endereco_destino`
	(cria um Endereco novo se `endereco_destino` for None). Usado no
	mecanismo de draft-copy do wizard de update: espelhar um Endereco do
	real pro draft (destino=None) e depois copiar de volta do draft pro
	real no commit final (destino=endereco do real)."""
	if endereco_origem is None:
		return endereco_destino
	dados = {campo: getattr(endereco_origem, campo) for campo in CAMPOS_ENDERECO}
	return criar_ou_atualizar_endereco(dados, endereco=endereco_destino)
