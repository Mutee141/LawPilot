from django.contrib import admin
from .models import Firm

@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'registration_number', 'email', 'phone')
