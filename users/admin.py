from django.contrib import admin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'username', 'email', 'password', 'first_name',
        'last_name', 'date_joined', 'last_login'
    )
    list_filter = (
        'id', 'username', 'email', 'password', 'first_name',
        'last_name', 'date_joined', 'last_login'
    )
    search_fields = (
        'id', 'username', 'email', 'password', 'first_name',
        'last_name', 'date_joined', 'last_login'
    )
