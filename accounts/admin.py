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

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'contato', 'tipo_usuario', 'is_active', 'is_superuser', 'password1', 'password2'),
        }),
    )

    list_display = ['id', 'username', 'email', 'contato', 'tipo_usuario', 'is_active', 'is_superuser', 'has_password']

    def has_password(self, obj):
        return obj.has_usable_password()
    has_password.boolean = True
    has_password.short_description = 'Senha utilizável?'



