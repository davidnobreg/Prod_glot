from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from base.models import Endereco

from .models import Empreendimento
from . import services as empreendimento_services

_WIZARD_UPDATE_SESSION_KEY = 'wizard_update'


def _copiar_logo(logo_origem, instance_destino):
	"""Copia o conteúdo de `logo_origem` (ImageField de outra instância)
	pro `logo` de `instance_destino` via ContentFile — nunca reaproveita o
	mesmo path de storage entre draft e real (cada Empreendimento tem seu
	próprio uuid no path, ver `_upload_logo_empreendimento` em models.py)."""
	if not logo_origem:
		return
	if instance_destino.logo:
		instance_destino.logo.delete(save=False)
	instance_destino.logo.save(
		logo_origem.name.rsplit('/', 1)[-1],
		ContentFile(logo_origem.read()),
		save=False,
	)


def _get_or_create_draft(request, empreendimento_uuid):
	"""Retorna (real, draft). Cria o draft (cópia inativa) na primeira
	chamada dessa sessão pra esse empreendimento; reaproveita nas
	seguintes via ponteiro salvo em `request.session`."""
	real = get_object_or_404(Empreendimento, uuid=empreendimento_uuid, is_ativo=True)

	wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
	session_key = str(empreendimento_uuid)
	draft_uuid = wizard_session.get(session_key, {}).get('draft_uuid')

	if draft_uuid:
		draft = Empreendimento.objects.filter(uuid=draft_uuid, is_ativo=False).first()
		if draft is not None:
			return real, draft

	endereco_empresa = empreendimento_services.sincronizar_endereco(None, real.endereco_empresa)
	endereco_empreendimento = empreendimento_services.sincronizar_endereco(None, real.endereco_empreendimento)

	draft = Empreendimento.objects.create(
		is_ativo=False,
		nome=real.nome,
		telefone=real.telefone,
		observacao=real.observacao,
		cnpj=None,  # nunca copiar: unique=True no banco colide com o do real (ver Global Constraints)
		razaoSocial=real.razaoSocial,
		codBanco=real.codBanco,
		banco=real.banco,
		agencia=real.agencia,
		conta=real.conta,
		matricula=real.matricula,
		cidade_foro=real.cidade_foro,
		tempo_reserva=real.tempo_reserva,
		quantidade_parcela=real.quantidade_parcela,
		desconto=real.desconto,
		tipo_correcao=real.tipo_correcao,
		endereco_empresa=endereco_empresa,
		endereco_empreendimento=endereco_empreendimento,
	)
	_copiar_logo(real.logo, draft)

	wizard_session[session_key] = {'draft_uuid': str(draft.uuid), 'cnpj_pendente': real.cnpj}
	request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
	request.session.modified = True

	return real, draft


def _deletar_draft(request, empreendimento_uuid):
	"""Apaga o draft (+ seus 2 enderecos + logo) e limpa o ponteiro da
	sessão. Não afeta o objeto real de forma alguma."""
	wizard_session = request.session.get(_WIZARD_UPDATE_SESSION_KEY, {})
	session_key = str(empreendimento_uuid)
	entrada = wizard_session.get(session_key)
	if entrada is None:
		return

	draft = Empreendimento.objects.filter(uuid=entrada['draft_uuid']).first()
	if draft is not None:
		if draft.endereco_empresa_id:
			Endereco.objects.filter(pk=draft.endereco_empresa_id).delete()
		if draft.endereco_empreendimento_id:
			Endereco.objects.filter(pk=draft.endereco_empreendimento_id).delete()
		if draft.logo:
			draft.logo.delete(save=False)
		draft.delete()

	del wizard_session[session_key]
	request.session[_WIZARD_UPDATE_SESSION_KEY] = wizard_session
	request.session.modified = True


@has_permission_decorator('alterarEmpreendimento')
@require_POST
def wizard_update_cancelar(request, empreendimento_uuid):
	_deletar_draft(request, empreendimento_uuid)
	return redirect('lista-empreendimento-tabela')
