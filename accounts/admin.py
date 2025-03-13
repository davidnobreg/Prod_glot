from django.contrib import admin

from .models import User


# Register your models here.
#admin.site.register(models.User)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'phone', 'tipo_usuario', 'is_active']