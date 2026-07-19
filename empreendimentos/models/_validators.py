from django.core.exceptions import ValidationError
from django.utils import timezone


def _validate_logo_arquivo(value):
    ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
    if ext not in ('jpg', 'jpeg'):
        raise ValidationError('Envie JPG ou PNG.')
    if value.size > 10 * 1024 * 1024:
        raise ValidationError('Arquivo não pode exceder 10 MB.')


def _upload_logo_empreendimento(instance, filename):
    return f'empreendimentos/{instance.uuid}/documentos/{filename}'


EXTENSOES_DOCUMENTO_WIZARD = ('pdf', 'jpg', 'jpeg', 'png', 'webp')
TAMANHO_MAXIMO_DOCUMENTO_WIZARD = 20 * 1024 * 1024  # 20MB


def _validate_documento_wizard(value):
    """Extensão + tamanho de documentos anexados no wizard (empreendimento
    e representante) — mesma convenção de `clientes.validators.validate_documento_representante`,
    implementação local pra não criar dependência empreendimentos → clientes."""
    ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
    if ext not in EXTENSOES_DOCUMENTO_WIZARD:
        raise ValidationError('Envie PDF, JPG, PNG ou WEBP.')
    if value.size > TAMANHO_MAXIMO_DOCUMENTO_WIZARD:
        raise ValidationError('Arquivo não pode exceder 20 MB.')


def _upload_documento_empreendimento(instance, filename):
    return f'empreendimentos/documentos/{timezone.now():%Y/%m}/{filename}'


def _upload_documento_representante(instance, filename):
    return f'empreendimentos/representantes/{timezone.now():%Y/%m}/{filename}'
