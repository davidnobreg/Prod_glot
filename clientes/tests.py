import io
import uuid as _uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import Cliente, _validate_doc_arquivo
from .forms import ClienteDocumentosForm
from django.core.exceptions import ValidationError


def _make_cliente():
    return Cliente.objects.create(
        uuid=_uuid.uuid4(),
        name='TESTE SILVA',
        documento='12345678901',
        email=f'teste_{_uuid.uuid4().hex[:6]}@exemplo.com',
    )


def _fake_file(name='doc.jpg', size=1024, content_type='image/jpeg'):
    content = b'X' * size
    return SimpleUploadedFile(name, content, content_type=content_type)


@override_settings(
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class ClienteDocumentosFormTest(TestCase):

    def test_upload_jpg_valido(self):
        cliente = _make_cliente()
        form = ClienteDocumentosForm(
            {},
            {'foto_rg_frente': _fake_file('rg_frente.jpg')},
            instance=cliente,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_upload_pdf_valido(self):
        cliente = _make_cliente()
        form = ClienteDocumentosForm(
            {},
            {'comprovante_residencia': _fake_file('comp.pdf', content_type='application/pdf')},
            instance=cliente,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_extensao_invalida_rejeitada(self):
        arquivo = _fake_file('virus.exe', content_type='application/octet-stream')
        try:
            _validate_doc_arquivo(arquivo)
            self.fail('Deveria ter levantado ValidationError')
        except ValidationError as e:
            self.assertIn('JPG', str(e))

    def test_arquivo_acima_10mb_rejeitado(self):
        arquivo = _fake_file('grande.jpg', size=11 * 1024 * 1024)
        try:
            _validate_doc_arquivo(arquivo)
            self.fail('Deveria ter levantado ValidationError')
        except ValidationError as e:
            self.assertIn('10 MB', str(e))
