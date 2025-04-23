from django.contrib import admin
from .models import User
from django.contrib.auth import admin as auth_admin
from .forms import UserCreationForm, UserChangeForm

@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    model = User
    fieldsets = auth_admin.UserAdmin.fieldsets + (
        ('Novos campos', {'fields': ('tipo_usuario','creci','contato')}),
    )
    list_display = ['id', 'username', 'email', 'contato', 'tipo_usuario', 'is_active', 'is_superuser']



