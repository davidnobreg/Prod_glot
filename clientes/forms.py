from django import forms
from .models import Cliente

## Cadastra Cliente    
class ClienteForm(forms.ModelForm):
    phone = forms.CharField(max_length=15, required=True)
    
    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo','id',)
        
    def __init__(self, *args, **kwargs): # Adiciona 
        super().__init__(*args, **kwargs)  
        for field_name, field in self.fields.items():   
              field.widget.attrs['class'] = 'form-control'