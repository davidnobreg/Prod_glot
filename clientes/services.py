"""Lógica de negócio de clientes que não cabe em model nem em view.

App `clientes` historicamente não tem camada de serviço (diferente de `vendas`);
este arquivo é o ponto de partida — lógica de representante legal (PJ) entra
aqui, não como função privada em `views.py`.
"""

from .models import ClienteRepresentante


def validar_representantes_pj(cliente):
	"""Retorna None se válido, ou mensagem de erro string se inválido.

	Regra: cliente PJ exige >=1 representante ativo. Representante casado
	exige conj_nome preenchido.
	"""
	representantes_ativos = cliente.representantes.filter(is_ativo=True)
	if not representantes_ativos.exists():
		return 'Cliente PJ precisa de ao menos um representante legal.'

	for representante in representantes_ativos:
		if representante.estado_civil == 'casado' and not (representante.conj_nome or '').strip():
			return f'Representante {representante.nome} é casado — informe o nome do cônjuge.'

	return None


def criar_representante(cliente, dados):
	"""Cria ClienteRepresentante vinculado a `cliente`. `dados` já validado
	(cleaned_data de ClienteRepresentanteForm)."""
	representante = ClienteRepresentante(cliente=cliente, **dados)
	representante.full_clean()
	representante.save()
	return representante


def remover_representante(representante_uuid, cliente):
	"""Remove representante do cliente.

	Decisão: hard delete se o cliente ainda é rascunho (is_ativo=False) —
	nada depende dele ainda, mesmo padrão de wizard_arquivo_del. Se o
	cliente já está ativo, soft-delete (is_ativo=False no representante)
	em vez de apagar — documento/contrato já gerado pode referenciar esse
	representante, hard delete destruiria histórico.
	"""
	try:
		representante = ClienteRepresentante.objects.get(uuid=representante_uuid, cliente=cliente)
	except ClienteRepresentante.DoesNotExist:
		return

	if cliente.is_ativo:
		representante.is_ativo = False
		representante.save(update_fields=['is_ativo'])
	else:
		representante.delete()
