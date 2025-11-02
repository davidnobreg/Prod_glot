from django import forms
from .models import Empreendimento, Lote

# Doc: https://docs.djangoproject.com/en/5.1/topics/http/file-uploads/

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


## Formulário para cadastro de Empreendimento
class EmpreendimentoForm(forms.ModelForm):
    class Meta:
        model = Empreendimento
        fields = '__all__'
        exclude = ('is_ativo',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})


## Formulário para upload de arquivos
class ArquivoForm(forms.Form):
    arquivo = forms.FileField(label="Arquivo", required=True)


## Formulário para cadastro de reserva temporário
class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ('cliente_reserva', 'telefone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica classes gerais e placeholders
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Máscara de telefone
        self.fields['telefone'].widget.attrs.update({
            'class': 'form-control mb-3 mask-phone',
            'placeholder': '(99) 99999-9999'
        })

        # Formata valor existente (edição)
        if self.instance and self.instance.telefone:
            tel = self.instance.telefone
            if len(tel) == 11:
                self.initial['telefone'] = f"({tel[:2]}) {tel[2:7]}-{tel[7:]}"
            elif len(tel) == 10:
                self.initial['telefone'] = f"({tel[:2]}) {tel[2:6]}-{tel[6:]}"
