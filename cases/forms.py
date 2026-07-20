from django import forms
from django.utils import timezone
from .models import Client, Case, Hearing, Court, Task, Invoice, CaseOrder 
from accounts.models import User

class ClientForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Choose a portal username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter portal password'}), required=True)

    class Meta:
        model = Client
        fields = ['full_name', 'cnic_id', 'phone', 'email', 'address', 'notes', 'username', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Customize specific fields
        self.fields['address'].widget.attrs.update({'rows': '3'})
        self.fields['notes'].widget.attrs.update({'rows': '3'})
        
        if self.instance.pk:
            # If editing, username and password are not required by default or should be handled differently
            self.fields['username'].required = False
            self.fields['password'].required = False
            self.fields['username'].widget.attrs['readonly'] = True
            self.fields['password'].help_text = "Leave blank to keep current password"

class SeniorLawyerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name if full_name else obj.username

class CaseForm(forms.ModelForm):
    assigned_senior_lawyer = SeniorLawyerChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Assign Senior Lawyer"
    )

    class Meta:
        model = Case
        fields = [
            'client', 'title', 'case_number', 'case_type', 'court', 
            'filing_date', 'first_hearing_date', 'doc', 'description', 'status', 'priority', 'assigned_senior_lawyer'
        ]
        widgets = {
            'filing_date': forms.DateInput(attrs={'type': 'date'}),
            'first_hearing_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.firm:
            self.fields['client'].queryset = Client.objects.filter(firm=user.firm)
            self.fields['assigned_senior_lawyer'].queryset = User.objects.filter(
                firm=user.firm, 
                role='senior_lawyer'
            )
            self.fields['assigned_senior_lawyer'].label = "Assign Senior Lawyer"
        
        # Check if the case is new or has no hearings
        has_hearings = False
        if self.instance and self.instance.pk:
            has_hearings = self.instance.hearings.exists()

        if not self.instance.pk or not has_hearings:
            self.fields['status'].choices = [('filed', 'Filed')]
            self.fields['status'].initial = 'filed'

        # Optional: Add Bootstrap classes to make dropdowns look nice
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

from django import forms
from .models import Hearing
from cases.models import Case


class HearingForm(forms.ModelForm):
    case_status = forms.ChoiceField(
        choices=Case.STATUS_CHOICES,
        required=False,
        label="Update Case Status",
        help_text="Update the case status based on this hearing.",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Hearing
        fields = [
            'case',
            'hearing_date',
            'hearing_outcome',
            'next_hearing_date',
            'document',
        ]

        widgets = {
            'hearing_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'next_hearing_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'hearing_outcome': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.case:
            self.fields['case_status'].initial = self.instance.case.status

        # Limit cases to user's firm
        if user and getattr(user, 'firm', None):
            base_qs = Case.objects.filter(firm=user.firm)
            if getattr(user, 'role', None) == 'senior_lawyer':
                from django.db.models import Q
                self.fields['case'].queryset = base_qs.filter(
                    Q(assigned_senior_lawyer=user) | 
                    Q(assigned_lawyers=user)
                ).distinct()
            elif getattr(user, 'role', None) == 'junior_lawyer':
                self.fields['case'].queryset = base_qs.filter(
                    assigned_lawyers=user
                ).distinct()
            else:
                self.fields['case'].queryset = base_qs

        # Add Bootstrap class to all fields
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs.update({'class': 'form-control'})


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'case',
            'title',
            'description',
            'assigned_to',
            'priority',
            'status',
            'deadline',
        ]


from django import forms
from django.utils import timezone
from .models import Invoice, Client, Case


class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = [
            'client',
            'case', 
            'invoice_number',
            'amount',
            'description',
            'status',
            'due_date',
            'paid_date',
        ]

        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select client'
            }),
            'case': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select case (optional)'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., INV-2024-001',
                'required': False
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the services or items being billed...'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'paid_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'Date when payment was received'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Store user reference for later use
        self.user = user

        # Always ensure querysets are set, even if user/firm is missing
        try:
            if user and hasattr(user, 'firm') and user.firm:
                # Primary: Filter by user's firm (multi-tenant security)
                client_queryset = Client.objects.filter(firm=user.firm).order_by('full_name')
                case_queryset = Case.objects.filter(firm=user.firm).order_by('case_number')
            else:
                # Fallback: Show all data if user/firm not available
                client_queryset = Client.objects.all().order_by('full_name')
                case_queryset = Case.objects.all().order_by('case_number')
            
            # Set the querysets
            self.fields['client'].queryset = client_queryset
            self.fields['case'].queryset = case_queryset
            
            # Debug: Log what we're doing
            print(f"Form init - User: {user}, Firm: {getattr(user, 'firm', None) if user else None}")
            print(f"Client queryset count: {client_queryset.count()}")
            print(f"Case queryset count: {case_queryset.count()}")
            
        except Exception as e:
            print(f"Error in form init: {e}")
            # Emergency fallback
            self.fields['client'].queryset = Client.objects.all()
            self.fields['case'].queryset = Case.objects.all()

        # Set initial values for new invoices
        if not self.instance.pk:
            # Auto-generate invoice number if not provided
            if not self.instance.invoice_number:
                self.fields['invoice_number'].initial = self.generate_invoice_number(user)

        # Field configurations
        self.fields['paid_date'].required = False
        self.fields['case'].required = False
        self.fields['description'].required = False
        self.fields['invoice_number'].required = False
        
        # Add help text
        self.fields['case'].help_text = "Optional: Select the related case for this invoice"
        self.fields['invoice_number'].help_text = "Leave blank to auto-generate"
        self.fields['paid_date'].help_text = "Required only when status is 'Paid'"
        self.fields['description'].help_text = "Detailed description of services rendered"

        # Add Bootstrap classes and styling
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'
            
            # Add required indicator
            if field.required:
                field.widget.attrs['required'] = 'required'

    def generate_invoice_number(self, user):
        """Generate unique invoice number"""
        if not user or not user.firm:
            return "INV-TEMP"
        
        import datetime
        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        
        # Count existing invoices for this month
        count = Invoice.objects.filter(
            firm=user.firm,
            created_at__year=year,
            created_at__month=month
        ).count()
        
        return f"INV-{year}-{month:02d}-{count + 1:03d}"

    def clean(self):
        cleaned_data = super().clean()

        amount = cleaned_data.get('amount')
        due_date = cleaned_data.get('due_date')
        paid_date = cleaned_data.get('paid_date')
        status = cleaned_data.get('status')

        # Amount validation
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0")

        # Due date validation
        if due_date:
            # Get issue_date from instance (auto_now_add field) or use today for new instances
            issue_date = getattr(self.instance, 'issue_date', None)
            if issue_date is None:
                issue_date = timezone.now().date()
            
            if due_date < issue_date:
                raise forms.ValidationError("Due date cannot be before issue date")
            
            if status == "draft" and due_date < timezone.now().date():
                raise forms.ValidationError("Draft invoice cannot have a past due date")

        # Paid status validation
        if status == "paid" and not paid_date:
            raise forms.ValidationError("Paid date is required when status is Paid")

        if paid_date and due_date and paid_date < due_date:
            # Optional: Allow payments before due date
            pass

        # Auto-generate invoice number if not provided
        if not cleaned_data.get('invoice_number'):
            cleaned_data['invoice_number'] = self.generate_invoice_number(self.user)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-set firm and created_by if not set
        if self.user:
            if not instance.firm:
                instance.firm = self.user.firm
            if not instance.created_by:
                instance.created_by = self.user
        
        # Auto-set paid_date if status changes to paid
        if instance.status == 'paid' and not instance.paid_date:
            instance.paid_date = timezone.now().date()
        
        if commit:
            instance.save()
        return instance


class CourtForm(forms.ModelForm):
    class Meta:
        model = Court
        fields = ['name', 'location', 'court_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter court name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter court location'
            }),
            'court_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'




class CaseOrderForm(forms.ModelForm):

    class Meta:
        model = CaseOrder
        fields = [
            'hearing',
            'case',
            'order_title',
            'order_type',
            'order_date',
            'summary',
            'order_document',
        ]

        widgets = {
            "case": forms.Select(attrs={
                "class": "form-select"
            }),
            "hearing": forms.Select(attrs={
                "class": "form-select"
            }),
            "order_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter order title"
            }),
            "order_type": forms.Select(attrs={
                "class": "form-select"
            }),
            "order_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "summary": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Provide a detailed summary of the court order..."
            }),
            "order_document": forms.FileInput(attrs={
                "class": "form-control",
                "accept": ".pdf,.doc,.docx"
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter cases by user's firm
        if user and hasattr(user, 'firm') and user.firm:
            self.fields['case'].queryset = Case.objects.filter(firm=user.firm)
            self.fields['hearing'].queryset = Hearing.objects.none()
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'

    def clean_order_document(self):
        document = self.cleaned_data.get('order_document')
        if document:
            # Check file size (10MB limit)
            if document.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Document size must be less than 10MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            file_extension = document.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError("Only PDF, DOC, and DOCX files are allowed.")
        
        return document

    def clean_order_date(self):
        order_date = self.cleaned_data.get('order_date')
        if order_date and order_date > timezone.now().date():
            raise forms.ValidationError("Order date cannot be in the future.")
        return order_date

from .models import DocumentCategory

class DocumentUploadForm(forms.Form):
    title = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Document Title'})
    )
    category = forms.ChoiceField(
        choices=DocumentCategory.choices, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )