from django.contrib import admin

# No models are currently registered for this app.
from django.contrib import admin
from .models import Justice, Judgment

@admin.register(Justice)
class JusticeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_judgment_count', 'created_at')
    search_fields = ('name',)

    def get_judgment_count(self, obj):
        return obj.judgments.count()
    get_judgment_count.short_description = 'Total Judgments'


@admin.register(Judgment)
class JudgmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'justice', 'uploaded_by', 'uploaded_at')
    list_filter = ('justice', 'uploaded_at')
    search_fields = ('title', 'case_number', 'justice__name')
    
    # Automatically assigns the logged-in Firm Owner/Admin as the uploader
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)