from django import forms

from ..models import DocumentoEmpreendimento, DocumentoRepresentante


class DocumentoEmpreendimentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoEmpreendimento
        fields = ('categoria', 'nome', 'arquivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].required = False
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control mb-3'})


class DocumentoRepresentanteForm(forms.ModelForm):
    class Meta:
        model = DocumentoRepresentante
        fields = ('categoria', 'nome', 'arquivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].required = False
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control mb-3'})
