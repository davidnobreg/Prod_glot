from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm, UserChangeForm as BaseUserChangeForm
from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'creci', 'contato', 'tipo_usuario']


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'creci', 'contato', 'tipo_usuario']


def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    for field in self.fields.values():
        field.widget.attrs['class'] = 'form-control'