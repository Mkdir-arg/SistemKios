from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User

_NEGOCIO = ("Negocio", {"fields": ("rol", "punto")})


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (_NEGOCIO,)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (_NEGOCIO,)
    list_display = ["username", "first_name", "last_name", "rol", "punto", "is_active"]
    list_filter = BaseUserAdmin.list_filter + ("rol", "punto")
    autocomplete_fields = ["punto"]
