from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm, UserChangeForm as BaseUserChangeForm
from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'creci', 'contato', 'tipo_usuario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica classes padrão de formatação
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Máscara e placeholder para telefone
        if 'contato' in self.fields:
            self.fields['contato'].widget.attrs.update({
                'class': 'form-control mb-3 mask-phone',
                'placeholder': '(99) 99999-9999'
            })

        # Formatação inicial (se houver valor)
        if self.instance and self.instance.contato:
            contato = self.instance.contato
            contato_num = ''.join(filter(str.isdigit, contato))
            if len(contato_num) > 10:
                # Celular
                self.initial['contato'] = f"({contato_num[:2]}) {contato_num[2:7]}-{contato_num[7:]}"
            elif len(contato_num) == 10:
                # Fixo
                self.initial['contato'] = f"({contato_num[:2]}) {contato_num[2:6]}-{contato_num[6:]}"


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'creci', 'contato', 'tipo_usuario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica classes padrão de formatação
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control mb-3'})

        # Máscara e placeholder para telefone
        if 'contato' in self.fields:
            self.fields['contato'].widget.attrs.update({
                'class': 'form-control mb-3 mask-phone',
                'placeholder': '(99) 99999-9999'
            })

        # Formatação inicial (se houver valor)
        if self.instance and self.instance.contato:
            contato = self.instance.contato
            contato_num = ''.join(filter(str.isdigit, contato))
            if len(contato_num) > 10:
                # Celular
                self.initial['contato'] = f"({contato_num[:2]}) {contato_num[2:7]}-{contato_num[7:]}"
            elif len(contato_num) == 10:
                # Fixo
                self.initial['contato'] = f"({contato_num[:2]}) {contato_num[2:6]}-{contato_num[6:]}"
