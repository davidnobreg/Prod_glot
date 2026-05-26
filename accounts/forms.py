from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm, UserChangeForm as BaseUserChangeForm
from .models import User


class FormMixin:
    """
    Mixin para aplicar classes de formulário, placeholder e formatação do telefone.
    """
    def apply_bootstrap(self):
        for field_name, field in self.fields.items():
            # Se for um campo booleano (checkbox)
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control mb-3'})

        # Personaliza o campo contato
        if 'contato' in self.fields:
            self.fields['contato'].widget.attrs.update({
                'class': 'form-control mb-3 mask-phone',
                'placeholder': '(99) 99999-9999'
            })
            if self.instance and self.instance.contato:
                self.initial['contato'] = self.format_telefone(self.instance.contato)

    @staticmethod
    def format_telefone(contato):
        contato_num = ''.join(filter(str.isdigit, contato))
        if len(contato_num) > 10:
            # Celular
            return f"({contato_num[:2]}) {contato_num[2:7]}-{contato_num[7:]}"
        elif len(contato_num) == 10:
            # Fixo
            return f"({contato_num[:2]}) {contato_num[2:6]}-{contato_num[6:]}"
        return contato

    def clean_contato(self):
        contato = self.cleaned_data.get('contato', '')
        contato_num = ''.join(filter(str.isdigit, contato))
        if len(contato_num) < 10:
            raise ValidationError("Telefone incompleto.")
        return contato_num


class UserCreationForm(BaseUserCreationForm, FormMixin):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'email', 'creci', 'contato', 'tipo_usuario', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Informe o e-mail.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Este e-mail ja esta cadastrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = user.email
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserChangeForm(BaseUserChangeForm, FormMixin):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'creci', 'contato', 'tipo_usuario', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        if 'username' in self.fields:
            self.fields['username'].disabled = True
            self.fields['username'].required = False
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Informe o e-mail.")

        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Este e-mail ja esta cadastrado.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = user.email
        if commit:
            user.save()
            self.save_m2m()
        return user
