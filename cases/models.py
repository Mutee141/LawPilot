from django.db import models
from django.conf import settings
import uuid
from firms.models import Firm
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.db import models
import os



class Court(models.Model):
    COURT_TYPES = [
        ('supreme', 'Supreme Court'),
        ('high', 'High Court'),
        ('district', 'District Court'),
        ('special', 'Special Court/Tribunal'),
    ]
    name = models.CharField(max_length=255)  
    location = models.CharField(max_length=255)
    court_type = models.CharField(max_length=20, choices=COURT_TYPES)


    def __str__(self):
        return f"{self.name} ({self.get_court_type_display()})"



class Client(models.Model):
    firm = models.ForeignKey(
        Firm,
        on_delete=models.CASCADE,
        related_name='clients'
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clients'
    )
    from django.conf import settings

    user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="client_profile"
    )
    
    full_name = models.CharField(max_length=255)
    cnic_id = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Case(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('filed', 'Filed'),
        ('pending', 'Pending'),
        ('arguments', 'Arguments'),
        ('reserved', 'Reserved for Judgment'),
        ('closed', 'Closed'),
        ('stayed', 'Stayed'),
    ]

    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('normal', 'Normal'),
        ('low', 'Low'),
    ]

    CASE_TYPES = [
        ('civil', 'Civil'),
        ('criminal', 'Criminal'),
        ('family', 'Family'),
        ('banking', 'Banking'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    firm = models.ForeignKey(
        Firm,
        on_delete=models.CASCADE,
        related_name='cases',
        db_index=True
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_cases'
    )

    assigned_lawyers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_cases',
        blank=True
    )

    assigned_senior_lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='senior_assigned_cases'
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='cases',
        null=True,
        blank=True
    )

    court = models.ForeignKey(
        Court,
        on_delete=models.PROTECT,
        related_name='cases',
        null=True,
        blank=True
    )


    case_number = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    doc = models.FileField(upload_to='case_docs/', blank=True, null=True)
    first_hearing_date = models.DateField(blank=True, null=True)
    case_type = models.CharField(max_length=20, choices=CASE_TYPES, blank=True, null=True)
    filing_date = models.DateField(blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    final_decision = models.TextField(blank=True, null=True)
    decision_date = models.DateField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='filed'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal'
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['firm', 'status']),
            models.Index(fields=['firm', 'priority']),
            models.Index(fields=['case_number']),
        ]
    def __str__(self):
        client_name = self.client.full_name if self.client else "No Client"
        return f"{self.case_number} - {client_name}"



class CaseHistory(models.Model):
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='case_histories', null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    case_id = models.CharField(max_length=100, blank=True, null=True)
    court = models.CharField(max_length=255, blank=True, null=True)
    court_outcome = models.TextField(blank=True, null=True)
    document = models.FileField(upload_to='case_history_docs/', blank=True, null=True, help_text="Upload Excel, PDF, Word, or CSV files here")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.case_id}"



class Hearing(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='hearings')

    hearing_date = models.DateTimeField()
    attended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    hearing_outcome = models.TextField(blank=True, null=True)
    court_remarks = models.TextField(blank=True, null=True) 

    adjournment_reason = models.CharField(max_length=255, blank=True, null=True)
    next_hearing_date = models.DateTimeField(blank=True, null=True)
    document = models.FileField(upload_to='hearing_documents/', blank=True, null=True)

    def __str__(self):
        return f"{self.case.case_number} | {self.hearing_date.date()}"
    
    def update_case_status(self):
        case = self.case
        outcome = (self.hearing_outcome or '').lower()
        reason = (self.adjournment_reason or '').lower()
        
        new_status = None
        
        if 'stay' in outcome or 'stay' in reason:
            new_status = 'stayed'
        elif any(kw in outcome for kw in ['closed', 'withdraw', 'compromise', 'settle']):
            new_status = 'closed'
        elif any(kw in outcome for kw in ['decide', 'judgment', 'dismiss', 'allow', 'decree', 'dispose']):
            new_status = 'decided'
        elif any(kw in outcome for kw in ['reserve', 'reserved']):
            new_status = 'reserved'
        elif any(kw in outcome for kw in ['argument', 'arguing', 'argued']):
            new_status = 'arguments'
        else:
            new_status = 'pending'
            
        if new_status:
            case.status = new_status
            case.save(update_fields=['status'])
    
    

class CaseOrder(models.Model):
    ORDER_TYPES = [
        ('interim', 'Interim Order'),
        ('final', 'Final Judgment'),
        ('stay', 'Stay Order'),
        ('direction', 'Court Direction'),
    ]

    hearing = models.ForeignKey(
        Hearing,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    order_title = models.CharField(max_length=255)

    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPES
    )

    order_date = models.DateField()

    summary = models.TextField()

    order_document = models.FileField(
        upload_to='court_orders/',
        blank=True,
        null=True
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )


    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f"{self.case.case_number} - {self.order_title}"
    


class Task(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    firm = models.ForeignKey('firms.Firm', on_delete=models.CASCADE)
    case = models.ForeignKey('Case', on_delete=models.CASCADE, related_name='tasks')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tasks"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks"
    )

    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    deadline = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_overdue(self):
        if self.deadline and self.status != "completed":
            return self.deadline < timezone.now().date()
        return False

    def __str__(self):
        return f"{self.title} - {self.case.case_number}"
    


class CaseActivity(models.Model):

    firm = models.ForeignKey('firms.Firm', on_delete=models.CASCADE)
    case = models.ForeignKey('Case', on_delete=models.CASCADE, related_name="activities")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.CharField(max_length=255)
    note = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.case.case_number} - {self.action}"


class Notification(models.Model):

    firm = models.ForeignKey('firms.Firm', on_delete=models.CASCADE)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    message = models.CharField(max_length=255)
    link = models.URLField(blank=True, null=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}"
    
    

class Invoice(models.Model):

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    )

    # Core Relations
    firm = models.ForeignKey(
        'firms.Firm',
        on_delete=models.CASCADE,
        related_name='invoices',
        db_index=True,
        null=True,
        blank=True
    )

    client = models.ForeignKey(
        'Client',
        on_delete=models.CASCADE,
        related_name='invoices'
    )

    case = models.ForeignKey(
        'Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )

    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Dates
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['firm', 'status']),
            models.Index(fields=['firm', 'created_at']),
            models.Index(fields=['client', 'status']),
        ]

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.client.full_name} - ₹{self.amount}"
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status not in ['pending', 'draft']:
            return False
        return self.due_date < timezone.now().date()



class DocumentCategory(models.TextChoices):
    PETITION = 'PET', 'Petition'
    EVIDENCE = 'EVI', 'Evidence'
    ORDER = 'ORD', 'Court Order'
    CLIENT_DOC = 'CLI', 'Client Document'
    OTHER = 'OTH', 'Other'

class CaseDocument(models.Model):
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=3, choices=DocumentCategory.choices, default=DocumentCategory.OTHER)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.title} - {self.case.case_number}"

def get_upload_path(instance, filename):
    # Organizes files by Case Number in the media folder
    return os.path.join('case_files', instance.document_main.case.case_number, filename)

class DocumentVersion(models.Model):
    document_main = models.ForeignKey(CaseDocument, on_delete=models.CASCADE, related_name='versions')
    file = models.FileField(upload_to=get_upload_path)
    version_number = models.IntegerField(default=1)
    notes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number'] # Latest version first

from django.db.models.signals import post_save
from django.dispatch import receiver
import pandas as pd
import os

@receiver(post_save, sender=CaseHistory)
def process_case_history_upload(sender, instance, created, **kwargs):
    if created and instance.document:
        try:
            file_path = instance.document.path
            if not os.path.exists(file_path):
                return
                
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            else:
                return # unsupported format
                
            records_to_create = []
            seen = set()
            for index, row in df.iterrows():
                values = [str(val).strip() if pd.notna(val) else '' for val in row.values]
                if not any(values):
                    continue
                    
                title = values[0] if len(values) > 0 and values[0] else 'Untitled'
                case_id = values[1] if len(values) > 1 else ''
                court = values[2] if len(values) > 2 else ''
                outcome = values[3] if len(values) > 3 else ''
                
                record_tuple = (title, case_id, court, outcome)
                if record_tuple in seen:
                    continue
                seen.add(record_tuple)
                
                exists = CaseHistory.objects.filter(
                    firm=instance.firm,
                    title=title,
                    case_id=case_id,
                    court=court,
                    court_outcome=outcome
                ).exists()
                
                if not exists:
                    records_to_create.append(
                        CaseHistory(
                            firm=instance.firm,
                            title=title,
                            case_id=case_id,
                            court=court,
                            court_outcome=outcome
                        )
                    )
            
            if records_to_create:
                CaseHistory.objects.bulk_create(records_to_create)
                CaseHistory.objects.filter(pk=instance.pk).update(title=f"Bulk Upload Container ({len(records_to_create)} items)")
                
        except Exception as e:
            pass

