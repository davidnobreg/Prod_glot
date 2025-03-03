from django import forms
from .models import RegisterVenda
from django.contrib.auth.models import User

## Registra de Venda    
class RegisterVendaForm(forms.ModelForm):
    user = User.username


    class Meta:
        model = RegisterVenda
        fields = ('cliente',)
        exclude = ('is_ativo', 'id',)
        
    
        
    def __init__(self, *args, **kwargs): # Adiciona 
        super().__init__(*args, **kwargs)  
        for field_name, field in self.fields.items():   
              field.widget.attrs['class'] = 'form-control'
