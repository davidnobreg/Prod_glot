from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplicando classes para controle geral
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Aplicando classes específicas para os campos com máscaras
        self.fields['documento'].widget.attrs.update({'class': 'form-control mb-3 mask-cpf'})
        self.fields['fone'].widget.attrs.update({'class': 'form-control mb-3 mask-phone'})

class ClienteModalForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = '__all__'
        exclude = ('is_ativo', 'id',)

    def __init__(self, *args, **kwargs): # Adiciona
        super().__init__(*args, **kwargs)
        self.fields['documento'].widget.attrs.update({'class': 'mask-cpf'})
        self.fields['fone'].widget.attrs.update({'class': 'mask-phone'})