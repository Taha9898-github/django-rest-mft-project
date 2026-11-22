from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin configuration for User model."""
    list_display = ['username', 'phone', 'fullname', 'email', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'phone', 'fullname', 'email']
    ordering = ['username']

    # Add phone and fullname to the admin forms
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'fullname')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('phone', 'fullname')}),
    )
