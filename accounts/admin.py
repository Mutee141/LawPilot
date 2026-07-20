from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # list_display controls the columns in the user list table
    list_display = ('username', 'email', 'firm', 'role', 'phone_number', 'is_staff')
    
    # fieldsets controls the "Edit User" page
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Information', {'fields': ('firm', 'role', 'phone_number', 'managed_by')}),
    )
    
    # add_fieldsets controls the "Add User" page
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Information', {'fields': ('firm', 'role', 'phone_number', 'managed_by')}),
    )

admin.site.register(User, CustomUserAdmin)