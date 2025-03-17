from django import forms
from .models import Cliente



class ClienteForm(forms.ModelForm):
    
    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo','id',)
        
    def __init__(self, *args, **kwargs): # Adiciona 
        super().__init__(*args, **kwargs)
        self.fields['documento'].widget.attrs.update({'class': 'mask-cpf'})
        self.fields['fone'].widget.attrs.update({'class': 'mask-phone'})
        #for field_name, field in self.fields.items():
            #  field.widget.attrs['class'] = 'form-control'

class ClienteModalForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id',)

    def __init__(self, *args, **kwargs): # Adiciona
        super().__init__(*args, **kwargs)
        self.fields['documento'].widget.attrs.update({'class': 'mask-cpf'})
        self.fields['fone'].widget.attrs.update({'class': 'mask-phone'})