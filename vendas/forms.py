from django import forms
from .models import RegisterVenda

class RegisterVendaForm(forms.ModelForm):
    class Meta:
        model = RegisterVenda
        fields = ('cliente',)  # Inclua os campos corretos do modelo
        exclude = ('is_ativo', 'id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
