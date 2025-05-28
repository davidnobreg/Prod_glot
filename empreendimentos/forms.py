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
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

## Cadastra um Imovel
class EmpreendimentoForm(forms.ModelForm):
    #Quadras = MultipleFileField()
    class Meta:
        model = Empreendimento
        fields = '__all__'
        exclude = ('is_ativo',)
        
    def __init__(self, *args, **kwargs): # Adiciona 
        super().__init__(*args, **kwargs)  
        for field_name, field in self.fields.items():   
            if field.widget.__class__ in [forms.CheckboxInput, forms.RadioSelect]:
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
    
## Formulario para cadastro atraves de arquivo
class ArquivoForm(forms.Form):
    arquivo = forms.FileField(label="Arquivo", required=True)

## Formulario para cadastro de reserva temporario
class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ('cliente_reserva','telefone')


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplicando classes para controle geral
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Aplicando classes específicas para os campos com máscaras
        self.fields['telefone'].widget.attrs.update({'class': 'form-control mb-3 mask-phone'})
