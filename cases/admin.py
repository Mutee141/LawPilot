from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Court, Client, Case, Hearing, CaseOrder, Task, Invoice, CaseDocument, DocumentVersion, CaseHistory

# --- Inlines ---

class HearingInline(admin.TabularInline):
    model = Hearing
    extra = 1
    fields = ('hearing_date', 'next_hearing_date', 'hearing_outcome', 'adjournment_reason')

class CaseOrderInline(admin.StackedInline):
    model = CaseOrder
    extra = 0
    fields = ('order_date', 'order_type', 'summary', 'order_document')

# --- Admin Classes ---

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ('name', 'court_type', 'location')
    list_filter = ('court_type',)
    search_fields = ('name', 'location')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'cnic_id', 'owner', 'created_at')
    search_fields = ('full_name', 'cnic_id', 'phone')
    list_filter = ('owner', 'created_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('case_number', 'client', 'court', 'status', 'priority', 'owner')
    list_filter = ('status', 'priority', 'case_type', 'court', 'owner')
    search_fields = ('case_number', 'client__full_name', 'court__name')
    inlines = [HearingInline, CaseOrderInline]
    date_hierarchy = 'filing_date'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(Hearing)
class HearingAdmin(admin.ModelAdmin):
    list_display = ('case', 'hearing_date', 'next_hearing_date', 'adjournment_reason')
    list_filter = ('hearing_date', 'next_hearing_date')
    search_fields = ('case__case_number', 'case__client__full_name')
    date_hierarchy = 'hearing_date'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(case__owner=request.user)

@admin.register(CaseOrder)
class CaseOrderAdmin(admin.ModelAdmin):
    list_display = ('case', 'order_type', 'order_date')
    list_filter = ('order_type', 'order_date')
    search_fields = ('case__case_number', 'summary')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(case__owner=request.user)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'case', 'assigned_to', 'status', 'priority', 'deadline', 'created_at')
    list_filter = ('status', 'priority', 'deadline', 'created_at')
    search_fields = ('title', 'description', 'case__case_number', 'assigned_to__username')
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(case__owner=request.user)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'client',
        'case',
        'amount',
        'status',
        'due_date',
        'created_at',
    )

    list_filter = (
        'status',
        'due_date',
        'created_at',
    )

    search_fields = (
        'client__full_name',
        'case__case_number',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Only show invoices from user's firm
        return qs.filter(client__firm=request.user.firm)

@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'case', 'category', 'created_at', 'uploaded_by')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'case__case_number')

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document_main', 'version_number', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('document_main__title', 'notes')

@admin.register(CaseHistory)
class CaseHistoryAdmin(ImportExportModelAdmin):
    list_display = ('title', 'case_id', 'court', 'firm', 'created_at')
    list_filter = ('firm', 'created_at')
    search_fields = ('title', 'case_id', 'court')