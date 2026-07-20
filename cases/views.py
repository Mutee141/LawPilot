from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from django.utils import timezone

from .models import Case, Client, Hearing, CaseOrder, Court, Task, Invoice, CaseActivity
from .forms import CaseForm, ClientForm, HearingForm, TaskForm, InvoiceForm, CourtForm, CaseOrderForm

from accounts.models import User

# ===================== PERMISSION HELPERS =====================

def can_access_billing(user):
    """Check if user can access billing/invoice features"""
    return user.role in ['accountant', 'firm_owner', 'senior_lawyer']


def billing_access_required(view_func):
    """Decorator to require billing access (accountant, firm_owner, or senior_lawyer)"""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not can_access_billing(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

# ===================== DASHBOARD VIEW =====================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_firm = self.request.user.firm
        user = self.request.user
        today = datetime.now()

        # Handle users without assigned firm
        if not user_firm:
            context['no_firm'] = True
            context['total_cases'] = 0
            context['active_cases'] = 0
            context['closed_cases'] = 0
            context['total_clients'] = 0
            context['total_lawyers'] = 0
            context['recent_cases'] = []
            context['upcoming_hearings'] = []
            context['todays_hearings'] = 0
            return context

        # Get firm-level stats
        context['total_cases'] = Case.objects.filter(firm=user_firm).count()
        context['active_cases'] = Case.objects.filter(
            firm=user_firm,
            status__in=['pending', 'arguments', 'reserved', 'filed']
        ).count()
        context['closed_cases'] = Case.objects.filter(
            firm=user_firm,
            status__in=['decided', 'closed']
        ).count()
        context['total_clients'] = Client.objects.filter(firm=user_firm).count()
        context['total_lawyers'] = user_firm.users.filter(role__in=['senior_lawyer', 'junior_lawyer']).count()

        # Get recent cases
        context['recent_cases'] = Case.objects.filter(firm=user_firm).order_by('-created_at')[:10]

        # Get upcoming hearings (next 7 days)
        next_week = today + timedelta(days=7)
        context['upcoming_hearings'] = Hearing.objects.filter(
            case__firm=user_firm,
            hearing_date__gte=today,
            hearing_date__lte=next_week
        ).order_by('hearing_date')[:10]

        # Get today's hearings
        context['todays_hearings'] = Hearing.objects.filter(
            case__firm=user_firm,
            hearing_date__date=today.date()
        ).count()

        # ==================== ROLE-SPECIFIC DATA ====================
        
        # Senior Lawyer specific data
        if user.role == 'senior_lawyer':
            # Get junior lawyers under this senior
            juniors = User.objects.filter(
                firm=user_firm,
                role="junior_lawyer",
                managed_by=user
            )

            # Fallback: if no juniors assigned directly, get all juniors in the firm
            if not juniors.exists():
                juniors = User.objects.filter(
                    firm=user_firm,
                    role="junior_lawyer"
                )

            junior_ids = juniors.values_list("id", flat=True)

            
            my_cases_qs = Case.objects.filter(
                firm=user_firm
            ).filter(
                Q(assigned_lawyers=user) |
                Q(assigned_senior_lawyer=user) |
                Q(assigned_lawyers__in=junior_ids)
            ).distinct()

            
            context['total_cases'] = my_cases_qs.count()

            
            end_date = today + timedelta(days=7)

            todays_hearings = Hearing.objects.filter(
                case__firm=user_firm
            ).filter(
                Q(case__assigned_lawyers=user) |
                Q(case__assigned_senior_lawyer=user) |
                Q(case__assigned_lawyers__in=junior_ids)
            ).filter(
                Q(hearing_date__date=today) | Q(next_hearing_date__date=today)
            ).distinct()

            upcoming_hearings = Hearing.objects.filter(
                case__firm=user_firm
            ).filter(
                Q(case__assigned_lawyers=user) |
                Q(case__assigned_senior_lawyer=user) |
                Q(case__assigned_lawyers__in=junior_ids)
            ).filter(
                Q(hearing_date__date__range=[today, end_date]) |
                Q(next_hearing_date__date__range=[today, end_date])
            ).distinct().order_by("hearing_date")

            
            context['todays_hearings_count'] = todays_hearings.count()
            context['upcoming_hearings_count'] = upcoming_hearings.count()
            context['todays_hearings_list'] = todays_hearings
            context['upcoming_hearings'] = upcoming_hearings

            
            junior_stats = []
            for junior in juniors:
                junior_stats.append({
                    "name": junior.get_full_name() or junior.username,
                    "cases": Case.objects.filter(
                        firm=user_firm
                    ).filter(
                        Q(assigned_lawyers=junior) | Q(owner=junior)
                    ).distinct().count(),
                    "tasks": Task.objects.filter(firm=user_firm, assigned_to=junior).count(),
                    "overdue": Task.objects.filter(firm=user_firm, assigned_to=junior, status="overdue").count(),
                })

            context['team_size'] = juniors.count()
            context['team_members'] = junior_stats

            
            from calendar import monthrange
            import calendar
            current_month = today.month
            current_year = today.year
            month_days = monthrange(current_year, current_month)[1]

           
            month_hearings_all = Hearing.objects.filter(
                case__firm=user_firm
            ).filter(
                Q(case__assigned_lawyers=user) |
                Q(case__assigned_senior_lawyer=user) |
                Q(case__assigned_lawyers__in=junior_ids)
            ).distinct().order_by("hearing_date")

           
            month_hearings_dates = month_hearings_all.filter(
                Q(hearing_date__year=current_year, hearing_date__month=current_month) |
                Q(next_hearing_date__year=current_year, next_hearing_date__month=current_month)
            ).values_list("hearing_date__date", flat=True)

            context['calendar_days'] = range(1, month_days + 1)
            context['month_hearing_dates'] = list(month_hearings_dates)
            context['calendar_hearings'] = month_hearings_all  # All hearings for calendar events
            context['today'] = today
            context['month_name'] = calendar.month_name[current_month]
            context['year'] = current_year

        return context


# ===================== CASE MANAGEMENT =====================

@login_required
def case_list(request):
    user = request.user
    firm = user.firm

    if user.role == 'firm_owner' or user.role == 'system_admin':
        # Owners and Admins see all cases in the firm
        cases = Case.objects.filter(firm=firm)
    elif user.role == 'senior_lawyer':
        # Senior lawyers see cases where they are the lead or assigned
        cases = Case.objects.filter(firm=firm).filter(
            Q(assigned_senior_lawyer=user) | Q(assigned_lawyers=user)
        ).distinct()
    elif user.role == 'junior_lawyer':
        # Junior lawyers see cases assigned to them
        cases = Case.objects.filter(firm=firm).filter(
            assigned_lawyers=user
        ).distinct()
    elif user.role == 'client':
        # Clients see only their own cases
        cases = Case.objects.filter(firm=firm, client__owner=user)
    else:
        # Fallback for other roles (empty list for security)
        cases = Case.objects.none()

    return render(request, "cases/case_list.html", {"cases": cases})


@login_required
def case_detail(request, pk):
    user = request.user
    case = get_object_or_404(Case, pk=pk, firm=user.firm)
    
    # Permission check
    if user.role == 'firm_owner' or user.role == 'system_admin':
        has_access = True
    elif user.role == 'senior_lawyer':
        has_access = (case.assigned_senior_lawyer == user or user in case.assigned_lawyers.all())
    elif user.role == 'junior_lawyer':
        has_access = (user in case.assigned_lawyers.all())
    elif user.role == 'client':
        has_access = (case.client and case.client.owner == user)
    else:
        has_access = False
                
    if not has_access:
        return redirect('case_list')
        
    return render(request, "cases/case_detail.html", {"case": case})


@login_required
def case_create(request):
    if request.user.role != 'firm_owner':
        return redirect('case_list')
    form = CaseForm(request.POST or None, user=request.user)

    if form.is_valid():
        case = form.save(commit=False)
        case.owner = request.user
        case.firm = request.user.firm
        case.save()
        CaseActivity.objects.create(
    firm=request.user.firm,
    case=case,
    user=request.user,
    action="Case Created"
)

        form.save_m2m()
        return redirect("case_list")

    return render(request, "cases/case_form.html", {"form": form})


@login_required
def case_update(request, pk):
    if request.user.role != 'firm_owner':
        return redirect('case_detail', pk=pk)
    case = get_object_or_404(Case, pk=pk, firm=request.user.firm)
    form = CaseForm(request.POST or None, instance=case, user=request.user)

    if form.is_valid():
        form.save()
        return redirect("case_detail", pk=pk)

    return render(request, "cases/case_form.html", {"form": form})


@login_required
def case_delete(request, pk):
    if request.user.role != "firm_owner":
        return redirect("dashboard")

    case = get_object_or_404(Case, pk=pk, firm=request.user.firm)

    if request.method == "POST":
        case.delete()
        return redirect("case_list")

    return render(request, "cases/case_confirm_delete.html", {"case": case})


# ===================== CLIENT MANAGEMENT =====================

@login_required
def client_list(request):
    clients = Client.objects.filter(firm=request.user.firm)
    return render(request, "cases/client_list.html", {"clients": clients})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk, firm=request.user.firm)
    return render(request, "cases/client_detail.html", {"client": client})


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)

    if form.is_valid():
        client = form.save(commit=False)
        client.firm = request.user.firm
        client.owner = request.user
        
        # Create User account for client portal
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        user = User.objects.create_user(
            username=username,
            password=password,
            firm=request.user.firm,
            role='client',
            first_name=client.full_name.split(' ')[0],
            last_name=' '.join(client.full_name.split(' ')[1:]) if len(client.full_name.split(' ')) > 1 else ''
        )
        
        client.user = user
        client.save()
        return redirect("client_list")

    return render(request, "cases/client_form.html", {"form": form})


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk, firm=request.user.firm)
    form = ClientForm(request.POST or None, instance=client)

    if form.is_valid():
        client = form.save()
        
        # Handle password update if provided
        password = form.cleaned_data.get('password')
        if password and client.user:
            client.user.set_password(password)
            client.user.save()
            
        return redirect("client_detail", pk=pk)

    return render(request, "cases/client_form.html", {"form": form})


# ===================== HEARING MANAGEMENT =====================

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Hearing

@login_required
def hearing_list(request):
    if not getattr(request.user, "firm", None):
        return render(request, "cases/hearing_list.html", {
            "upcoming_hearings": [],
            "todays_hearings": [],
            "completed_hearings": [],
        })

    today = timezone.localdate()

    user = request.user
    base_queryset = Hearing.objects.select_related(
        "case",
        "case__court",
        "case__owner",
    ).filter(case__firm=user.firm)

    if user.role == 'senior_lawyer':
        base_queryset = base_queryset.filter(
            Q(case__assigned_senior_lawyer=user) | Q(case__assigned_lawyers=user)
        ).distinct()
    elif user.role == 'junior_lawyer':
        base_queryset = base_queryset.filter(
            case__assigned_lawyers=user
        ).distinct()
    elif user.role == 'client':
        base_queryset = base_queryset.filter(
            case__client__owner=user
        )

    todays_hearings = base_queryset.filter(
        hearing_date__date=today
    ).order_by("hearing_date")

    upcoming_hearings = base_queryset.filter(
        hearing_date__date__gt=today
    ).order_by("hearing_date")

    completed_hearings = base_queryset.filter(
        hearing_date__date__lt=today
    ).order_by("-hearing_date")

    context = {
        "upcoming_hearings": upcoming_hearings[:20],
        "todays_hearings": todays_hearings,
        "completed_hearings": completed_hearings[:20],
    }

    return render(request, "cases/hearing_list.html", context)


@login_required
def hearing_detail(request, pk):
    hearing = get_object_or_404(Hearing, pk=pk, case__firm=request.user.firm)
    return render(request, "cases/hearing_detail.html", {"hearing": hearing})


@login_required
def hearing_create(request):
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        return redirect('hearing_list')

    if not getattr(request.user, "firm", None):
        return render(request, "cases/hearing_form.html", {
            "form": HearingForm(None, user=request.user),
            "case": None,
            "upcoming_hearings": [],
            "todays_hearings": [],
            "completed_hearings": [],
        })

    case_id = request.GET.get("case") or request.POST.get("case")
    case_obj = None

    if case_id:
        try:
            case_obj = Case.objects.get(
                pk=case_id,
                firm=request.user.firm
            )
        except Case.DoesNotExist:
            case_obj = None

    form = HearingForm(request.POST or None, request.FILES or None, user=request.user)

    if form.is_valid():
        hearing = form.save(commit=False)

        if case_obj:
            hearing.case = case_obj

        # 🔴 CRITICAL SAFETY CHECK
        if not hearing.case:
            form.add_error("case", "Please select a valid case.")
        elif hearing.case.firm != request.user.firm:
            form.add_error("case", "Invalid case selection.")
        else:
            hearing.save()
            
            # Update case status
            case_status = form.cleaned_data.get('case_status')
            if case_status and case_status != hearing.case.status:
                hearing.case.status = case_status
                hearing.case.save()
            else:
                hearing.update_case_status()
                
            return redirect("hearing_list")

    # Get hearing statistics for dashboard
    today = timezone.localdate()
    
    base_queryset = Hearing.objects.select_related(
        "case",
        "case__court",
        "case__owner",
    ).filter(
        case__firm=request.user.firm
    )

    todays_hearings = base_queryset.filter(
        hearing_date__date=today
    ).order_by("hearing_date")

    upcoming_hearings = base_queryset.filter(
        hearing_date__date__gt=today
    ).order_by("hearing_date")

    completed_hearings = base_queryset.filter(
        hearing_date__date__lt=today
    ).order_by("-hearing_date")

    context = {
        "form": form,
        "case": case_obj,
        "upcoming_hearings": upcoming_hearings[:20],
        "todays_hearings": todays_hearings,
        "completed_hearings": completed_hearings[:20],
    }

    return render(request, "cases/hearing_form.html", context)


@login_required
def hearing_edit(request, pk):
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        return redirect('hearing_detail', pk=pk)
        
    hearing = get_object_or_404(Hearing, pk=pk, case__firm=request.user.firm)
    form = HearingForm(request.POST or None, request.FILES or None, instance=hearing, user=request.user)

    if form.is_valid():
        hearing = form.save()
        
        # Update case status
        case_status = form.cleaned_data.get('case_status')
        if case_status and case_status != hearing.case.status:
            hearing.case.status = case_status
            hearing.case.save()
        else:
            hearing.update_case_status()
            
        return redirect("hearing_detail", pk=pk)

    # Get hearing statistics for dashboard
    today = timezone.localdate()
    
    base_queryset = Hearing.objects.select_related(
        "case",
        "case__court",
        "case__owner",
    ).filter(
        case__firm=request.user.firm
    )

    todays_hearings = base_queryset.filter(
        hearing_date__date=today
    ).order_by("hearing_date")

    upcoming_hearings = base_queryset.filter(
        hearing_date__date__gt=today
    ).order_by("hearing_date")

    completed_hearings = base_queryset.filter(
        hearing_date__date__lt=today
    ).order_by("-hearing_date")

    context = {
        "form": form,
        "upcoming_hearings": upcoming_hearings[:20],
        "todays_hearings": todays_hearings,
        "completed_hearings": completed_hearings[:20],
    }

    return render(request, "cases/hearing_form.html", context)


@login_required
def hearing_delete(request, pk):
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        return redirect('hearing_list')
        
    hearing = get_object_or_404(Hearing, pk=pk, case__firm=request.user.firm)
    
    if request.method == "POST":
        hearing.delete()
        return redirect("hearing_list")
        
    return render(request, "cases/hearing_confirm_delete.html", {"hearing": hearing})


# ===================== INVOICE MANAGEMENT =====================

@billing_access_required
def invoice_list(request):
    """List all invoices for the firm with filtering and pagination"""
    user = request.user
    firm = user.firm
    
    # Get all invoices for the firm
    invoices = Invoice.objects.filter(firm=firm).select_related(
        'client', 'case', 'created_by'
    ).order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    if client_filter:
        invoices = invoices.filter(client_id=client_filter)
    
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(client__full_name__icontains=search_query) |
            Q(case__case_number__icontains=search_query)
        )
    
    # Get summary statistics
    total_amount = invoices.aggregate(Sum('amount'))['amount__sum'] or 0
    paid_amount = invoices.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_amount = invoices.filter(status__in=['pending', 'draft']).aggregate(Sum('amount'))['amount__sum'] or 0
    overdue_amount = invoices.filter(status='overdue').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get clients for filter dropdown
    clients = Client.objects.filter(firm=firm).order_by('full_name')
    
    context = {
        'invoices': invoices,
        'clients': clients,
        'status_choices': Invoice.STATUS_CHOICES,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'overdue_amount': overdue_amount,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'search_query': search_query,
    }
    return render(request, 'cases/invoice_list.html', context)


@billing_access_required
def invoice_create(request):

    user = request.user
    firm = user.firm

    if request.method == "POST":
        form = InvoiceForm(request.POST, user=user)

        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.firm = firm
            invoice.created_by = user
            invoice.save()

            return redirect("invoice_detail", pk=invoice.pk)

    else:
        form = InvoiceForm(user=user)

    context = {
        "form": form,
        "title": "Create New Invoice",
    }

    return render(
        request,
        "cases/invoice_form.html",
        context,
    )


@billing_access_required
def invoice_detail(request, pk):
    """View and edit invoice details"""
    user = request.user
    firm = user.firm
    
    invoice = get_object_or_404(Invoice, pk=pk, firm=firm)
    
    # Check permission to edit
    can_edit = user.role == 'firm_owner' or (user.role == 'accountant' and user.firm == firm)
    
    if request.method == 'POST':
        if not can_edit:
            return redirect('invoice_detail', pk=pk)
        
        form = InvoiceForm(request.POST, instance=invoice, user=user)
        if form.is_valid():
            form.save()
            return redirect('invoice_detail', pk=pk)
    else:
        form = InvoiceForm(instance=invoice, user=user)
    
    # Calculate metrics
    days_until_due = (invoice.due_date - timezone.now().date()).days if invoice.due_date else None
    is_overdue = invoice.is_overdue()
    
    context = {
        'invoice': invoice,
        'form': form,
        'can_edit': can_edit,
        'days_until_due': days_until_due,
        'is_overdue': is_overdue,
    }
    return render(request, 'cases/invoice_detail.html', context)


@billing_access_required
def invoice_delete(request, pk):
    """Delete an invoice (only draft and pending invoices)"""
    user = request.user
    firm = user.firm
    
    invoice = get_object_or_404(Invoice, pk=pk, firm=firm)
    
    # Only allow deletion of draft/pending invoices
    if invoice.status not in ['draft', 'pending']:
        return redirect('invoice_detail', pk=pk)
    
    # Only firm owner can delete
    if user.role != 'firm_owner':
        return redirect('invoice_detail', pk=pk)
    
    if request.method == 'POST':
        invoice.delete()
        return redirect('invoice_list')
    
    context = {'invoice': invoice}
    return render(request, 'cases/invoice_confirm_delete.html', context)


@billing_access_required
def invoice_mark_paid(request, pk):
    """Mark invoice as paid"""
    user = request.user
    firm = user.firm
    
    invoice = get_object_or_404(Invoice, pk=pk, firm=firm)
    
    # Only accountant or firm owner can mark as paid
    if user.role not in ['accountant', 'firm_owner']:
        return redirect('invoice_detail', pk=pk)
    
    if request.method == 'POST':
        invoice.status = 'paid'
        invoice.paid_date = timezone.now().date()
        invoice.save()
        return redirect('invoice_detail', pk=pk)
    
    context = {'invoice': invoice}
    return render(request, 'cases/invoice_confirm_paid.html', context)

# ===================== COURTS MANAGEMENT =====================

@login_required
def court_list(request):
    """List all courts"""
    courts = Court.objects.all()
    context = {'courts': courts}
    return render(request, 'cases/court_list.html', context)


@login_required
def court_detail(request, pk):
    """View court details"""
    court = get_object_or_404(Court, pk=pk)
    context = {'court': court}
    return render(request, 'cases/court_detail.html', context)


@login_required
def court_create(request):
    """Create new court"""
    if request.user.role not in ['firm_owner', 'senior_lawyer']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = CourtForm(request.POST)
        if form.is_valid():
            court = form.save()
            return redirect('court_detail', pk=court.pk)
    else:
        form = CourtForm()
    
    return render(request, 'cases/court_form.html', {'form': form, 'court': None})


@login_required
def court_update(request, pk):
    """Update court information"""
    if request.user.role not in ['firm_owner', 'senior_lawyer']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    court = get_object_or_404(Court, pk=pk)
    
    if request.method == 'POST':
        form = CourtForm(request.POST, instance=court)
        if form.is_valid():
            form.save()
            return redirect('court_detail', pk=court.pk)
    else:
        form = CourtForm(instance=court)
    
    return render(request, 'cases/court_form.html', {'form': form, 'court': court})


@login_required
def court_delete(request, pk):
    """Delete court"""
    if request.user.role not in ['firm_owner', 'senior_lawyer']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    court = get_object_or_404(Court, pk=pk)
    
    if request.method == 'POST':
        court.delete()
        return redirect('court_list')
    
    context = {'court': court}
    return render(request, 'cases/court_confirm_delete.html', context)




@login_required
def staff_list(request):
    context = {}
    return render(request, "accounts/staff_list.html", context)


@login_required
def order_create(request):
    context = {}
    return render(request, "cases/case_form.html", context)



@login_required
def task_list(request):
    tasks = Task.objects.filter(firm=request.user.firm)

    if request.user.role == "junior_lawyer":
        tasks = tasks.filter(assigned_to=request.user)

    return render(request, "tasks/task_list.html", {"tasks": tasks})


@login_required
def task_create(request):
    form = TaskForm(request.POST or None)

    if form.is_valid():
        task = form.save(commit=False)
        task.firm = request.user.firm
        task.created_by = request.user
        task.save()
        CaseActivity.objects.create(
    firm=request.user.firm,
    case=task.case,
    user=request.user,
    action="Task Created",
    note=task.title
)

        return redirect("task_list")

    return render(request, "tasks/task_form.html", {"form": form})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, firm=request.user.firm)

    form = TaskForm(request.POST or None, instance=task)

    if form.is_valid():
        form.save()
        return redirect("task_list")

    return render(request, "tasks/task_form.html", {"form": form})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, firm=request.user.firm)

    if request.method == "POST":
        task.delete()

    return render(request, "tasks/task_confirm_delete.html", {"task": task})

@login_required
def create_case_order(request, hearing_id):
    hearing = get_object_or_404(Hearing, id=hearing_id)

    form = CaseOrderForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        order = form.save(commit=False)
        order.uploaded_by = request.user
        order.hearing = hearing
        order.case = hearing.case
        order.save()

        return redirect('hearing_detail', hearing_id)

    return render(request, "cases/order_form.html", {
        "form": form,
        "hearing": hearing
    })


# ===================== CASE ORDERS MANAGEMENT =====================

@login_required
def case_order_list_senior(request):
    """Senior Lawyer - Full access to case orders"""
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    orders = CaseOrder.objects.filter(
        case__firm=request.user.firm
    ).select_related('case', 'hearing', 'uploaded_by').order_by('-order_date')
    
    # Filter options
    case_id = request.GET.get('case')
    order_type = request.GET.get('type')
    
    if case_id:
        orders = orders.filter(case_id=case_id)
    if order_type:
        orders = orders.filter(order_type=order_type)
    
    # Get filter options
    cases = Case.objects.filter(firm=request.user.firm)
    
    context = {
        'orders': orders,
        'cases': cases,
        'order_types': CaseOrder.ORDER_TYPES,
        'selected_case': case_id,
        'selected_type': order_type,
        'user_role': 'senior_lawyer'
    }
    return render(request, 'cases/orders/senior_lawyer_list.html', context)


@login_required
def case_order_list_junior(request):
    """Junior Lawyer - Limited access to assigned case orders"""
    if request.user.role != 'junior_lawyer':
        if request.user.role == 'senior_lawyer':
            return redirect('senior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    # Junior lawyers can only see orders from cases they're assigned to
    orders = CaseOrder.objects.filter(
        case__firm=request.user.firm,
        case__assigned_lawyers=request.user
    ).select_related('case', 'hearing', 'uploaded_by').order_by('-order_date')
    
    # Filter options
    case_id = request.GET.get('case')
    order_type = request.GET.get('type')
    
    if case_id:
        orders = orders.filter(case_id=case_id)
    if order_type:
        orders = orders.filter(order_type=order_type)
    
    # Get filter options (only assigned cases)
    cases = Case.objects.filter(
        firm=request.user.firm,
        assigned_lawyers=request.user
    )
    
    context = {
        'orders': orders,
        'cases': cases,
        'order_types': CaseOrder.ORDER_TYPES,
        'selected_case': case_id,
        'selected_type': order_type,
        'user_role': 'junior_lawyer'
    }
    return render(request, 'cases/orders/junior_lawyer_list.html', context)


@login_required
def case_order_list_client(request):
    """Client Portal - View only access to their case orders"""
    if request.user.role != 'client':
        if request.user.role == 'senior_lawyer':
            return redirect('senior_dashboard')
        elif request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    # Get client profile
    try:
        client = request.user.client_profile
    except Client.DoesNotExist:
        return redirect('dashboard_redirect')
    
    # Clients can only see orders from their cases
    orders = CaseOrder.objects.filter(
        case__client=client
    ).select_related('case', 'hearing', 'uploaded_by').order_by('-order_date')
    
    # Filter options
    case_id = request.GET.get('case')
    order_type = request.GET.get('type')
    
    if case_id:
        orders = orders.filter(case_id=case_id)
    if order_type:
        orders = orders.filter(order_type=order_type)
    
    # Get filter options (only client's cases)
    cases = Case.objects.filter(client=client)
    
    context = {
        'orders': orders,
        'cases': cases,
        'order_types': CaseOrder.ORDER_TYPES,
        'selected_case': case_id,
        'selected_type': order_type,
        'user_role': 'client'
    }
    return render(request, 'cases/orders/client_list.html', context)


@login_required
def case_order_list_admin(request):
    """Admin/Firm Owner - Full access to all firm orders"""
    if request.user.role != 'firm_owner':
        if request.user.role == 'senior_lawyer':
            return redirect('senior_dashboard')
        elif request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    orders = CaseOrder.objects.filter(
        case__firm=request.user.firm
    ).select_related('case', 'hearing', 'uploaded_by', 'case__client').order_by('-order_date')
    
    # Filter options
    case_id = request.GET.get('case')
    order_type = request.GET.get('type')
    lawyer_id = request.GET.get('lawyer')
    
    if case_id:
        orders = orders.filter(case_id=case_id)
    if order_type:
        orders = orders.filter(order_type=order_type)
    if lawyer_id:
        orders = orders.filter(uploaded_by_id=lawyer_id)
    
    # Get filter options
    cases = Case.objects.filter(firm=request.user.firm)
    lawyers = request.user.firm.users.filter(role__in=['senior_lawyer', 'junior_lawyer'])
    
    context = {
        'orders': orders,
        'cases': cases,
        'lawyers': lawyers,
        'order_types': CaseOrder.ORDER_TYPES,
        'selected_case': case_id,
        'selected_type': order_type,
        'selected_lawyer': lawyer_id,
        'user_role': 'firm_owner'
    }
    return render(request, 'cases/orders/admin_list.html', context)


@login_required
def case_order_create(request, hearing_id=None, case_id=None):
    """Create new case order - Senior lawyers and firm owners only"""
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    # Initialize variables
    hearing = None
    case = None
    
    if hearing_id:
        hearing = get_object_or_404(Hearing, id=hearing_id)
        case = hearing.case
        # Check if user has access to this case
        if case.firm != request.user.firm:
            return redirect('dashboard_redirect')
    elif case_id:
        case = get_object_or_404(Case, id=case_id)
        hearing = None
        # Check if user has access to this case
        if case.firm != request.user.firm:
            return redirect('dashboard_redirect')
    else:
        # Get cases for selection
        cases = Case.objects.filter(firm=request.user.firm)
        if request.method == 'POST':
            case_id = request.POST.get('case')
            if case_id:
                case = get_object_or_404(Case, id=case_id, firm=request.user.firm)
            else:
                return redirect('dashboard_redirect')
        else:
            context = {'cases': cases}
            return render(request, 'cases/orders/select_case.html', context)
    
    if request.method == 'POST':
        form = CaseOrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.uploaded_by = request.user
            order.case = case
            if hearing:
                order.hearing = hearing
            order.save()
            
            # Create activity log
            CaseActivity.objects.create(
                firm=request.user.firm,
                case=case,
                user=request.user,
                action="Court Order Created",
                note=f"Order: {order.order_title}"
            )
            
            return redirect('case_order_detail', order.id)
    else:
        initial_data = {'case': case}
        if hearing:
            initial_data['hearing'] = hearing
        form = CaseOrderForm(initial=initial_data)
        
        # Limit hearing choices to this case
        if case:
            form.fields['hearing'].queryset = Hearing.objects.filter(case=case)
    
    context = {
        'form': form,
        'case': case,
        'hearing': hearing,
        'action': 'Create'
    }
    return render(request, 'cases/orders/order_form.html', context)


@login_required
def case_order_detail(request, order_id):
    """View case order details - Role-based access"""
    order = get_object_or_404(CaseOrder, id=order_id)
    
    # Check access based on user role
    if request.user.role == 'client':
        # Clients can only see their own case orders
        if order.case.client.user != request.user:
            return redirect('dashboard_redirect')
    elif request.user.role == 'junior_lawyer':
        # Junior lawyers can only see orders from assigned cases
        if not order.case.assigned_lawyers.filter(id=request.user.id).exists():
            return redirect('dashboard_redirect')
    elif request.user.role in ['senior_lawyer', 'firm_owner']:
        # Senior lawyers and firm owners can see all firm orders
        if order.case.firm != request.user.firm:
            return redirect('dashboard_redirect')
    else:
        return redirect('dashboard_redirect')
    
    context = {
        'order': order,
        'user_role': request.user.role,
        'can_edit': request.user.role in ['senior_lawyer', 'firm_owner']
    }
    return render(request, 'cases/orders/order_detail.html', context)


@login_required
def case_order_edit(request, order_id):
    """Edit case order - Senior lawyers and firm owners only"""
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    order = get_object_or_404(CaseOrder, id=order_id)
    
    # Check if user has access to this order
    if order.case.firm != request.user.firm:
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = CaseOrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            
            # Create activity log
            CaseActivity.objects.create(
                firm=request.user.firm,
                case=order.case,
                user=request.user,
                action="Court Order Updated",
                note=f"Order: {order.order_title}"
            )
            
            return redirect('case_order_detail', order.id)
    else:
        form = CaseOrderForm(instance=order)
        # Limit hearing choices to this case
        form.fields['hearing'].queryset = Hearing.objects.filter(case=order.case)
    
    context = {
        'form': form,
        'order': order,
        'case': order.case,
        'action': 'Edit'
    }
    return render(request, 'cases/orders/order_form.html', context)


@login_required
def case_order_delete(request, order_id):
    """Delete case order - Senior lawyers and firm owners only"""
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        if request.user.role == 'junior_lawyer':
            return redirect('junior_dashboard')
        elif request.user.role == 'client':
            return redirect('client_dashboard')
        elif request.user.role == 'firm_owner':
            return redirect('owner_dashboard')
        else:
            return redirect('dashboard_redirect')
    
    order = get_object_or_404(CaseOrder, id=order_id)
    
    # Check if user has access to this order
    if order.case.firm != request.user.firm:
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        case = order.case
        order_title = order.order_title
        order.delete()
        
        # Create activity log
        CaseActivity.objects.create(
            firm=request.user.firm,
            case=case,
            user=request.user,
            action="Court Order Deleted",
            note=f"Order: {order_title}"
        )
        
        return redirect('case_order_list_senior')
    
    context = {'order': order}
    return render(request, 'cases/orders/order_confirm_delete.html', context)


from django.shortcuts import render, get_object_or_404, redirect
from .models import CaseDocument, DocumentVersion
from .forms import DocumentUploadForm 

def upload_document(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Create the Main Document Entry
            doc = CaseDocument.objects.create(
                case=case,
                title=form.cleaned_data['title'],
                category=form.cleaned_data['category'],
                uploaded_by=request.user
            )
            # 2. Create the first Version
            DocumentVersion.objects.create(
                document_main=doc,
                file=request.FILES['file'],
                version_number=1,
                notes="Initial Upload"
            )
            return redirect('case_detail', pk=case_id)
    return render(request, 'cases/upload_doc.html', {'case': case})

from django.core.exceptions import PermissionDenied

def delete_document(request, doc_id):
    document = get_object_or_404(CaseDocument, id=doc_id)
    
    # Professional check: Only the Senior Lawyer or the Owner of the firm can delete
    if request.user.role != 'SENIOR_LAWYER' and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to delete legal records.")
    
    document.delete()
    return redirect('case_detail', pk=document.case.id)


import csv
from .models import CaseHistory

@login_required
def case_history_list(request):
    if request.user.role not in ['firm_owner', 'senior_lawyer', 'junior_lawyer']:
        return redirect('dashboard_redirect')
    histories = CaseHistory.objects.filter(firm=request.user.firm).order_by('-created_at')
    return render(request, 'cases/case_history_list.html', {'histories': histories})

import pandas as pd

@login_required
def case_history_upload(request):
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        upload_file = request.FILES.get('csv_file')
        if not upload_file:
            messages.error(request, "Please upload a CSV or Excel file.")
            return redirect('case_history_upload')
            
        filename = upload_file.name.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xls') or filename.endswith('.xlsx')):
            messages.error(request, "This is not a valid file. Please upload a CSV or Excel file.")
            return redirect('case_history_upload')
            
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(upload_file)
            else:
                df = pd.read_excel(upload_file)
                
            count = 0
            seen = set()
            for index, row in df.iterrows():
                # Extract values safely
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
                    firm=request.user.firm,
                    title=title,
                    case_id=case_id,
                    court=court,
                    court_outcome=outcome
                ).exists()
                
                if not exists:
                    CaseHistory.objects.create(
                        firm=request.user.firm,
                        title=title,
                        case_id=case_id,
                        court=court,
                        court_outcome=outcome
                    )
                    count += 1
                
            messages.success(request, f"Successfully uploaded {count} case histories.")
            return redirect('case_history_list')
        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('case_history_upload')
            
    return render(request, 'cases/case_history_upload.html')

@login_required
def reports_dashboard(request):
    """
    Reports Dashboard
    1. Case History (All for owner, assigned for senior_lawyer)
    2. Monthly Filed Cases (Firm owner only)
    3. Cases Assigned per User by Role (Firm owner only)
    """
    from django.db.models import Prefetch, Q
    user = request.user
    
    if user.role not in ['firm_owner', 'senior_lawyer']:
        messages.error(request, "You do not have permission to view reports.")
        return redirect('dashboard_redirect')
        
    context = {}
    
    if user.role == 'firm_owner':
        cases_qs = Case.objects.filter(firm=user.firm)
    else:
        cases_qs = Case.objects.filter(
            Q(owner=user) | 
            Q(assigned_senior_lawyer=user) | 
            Q(assigned_lawyers=user)
        ).filter(firm=user.firm).distinct()
        
    # 1. Case History
    activities_prefetch = Prefetch(
        'activities',
        queryset=CaseActivity.objects.order_by('-timestamp')
    )
    cases_with_history = cases_qs.prefetch_related(activities_prefetch).order_by('-created_at')
    context['case_history_list'] = cases_with_history
    
    # Reports 2 & 3 (Firm Owner only)
    if user.role == 'firm_owner':
        # 2. Monthly Filed Cases
        monthly_cases = {}
        for c in cases_qs.prefetch_related('assigned_lawyers', 'assigned_senior_lawyer', 'owner'):
            dt = c.filing_date if c.filing_date else c.created_at.date()
            if dt:
                month_key = dt.strftime('%B %Y')
                if month_key not in monthly_cases:
                    monthly_cases[month_key] = []
                monthly_cases[month_key].append(c)
        context['monthly_cases'] = monthly_cases
        
        # 3. Cases Assigned per User by Role
        from accounts.models import User
        users = User.objects.filter(firm=user.firm).order_by('role', 'first_name')
        user_case_stats = []
        for u in users:
            count = Case.objects.filter(
                Q(owner=u) | 
                Q(assigned_senior_lawyer=u) | 
                Q(assigned_lawyers=u)
            ).filter(firm=user.firm).distinct().count()
            
            user_case_stats.append({
                'user': u,
                'role': u.get_role_display(),
                'case_count': count
            })
        context['user_case_stats'] = user_case_stats

    return render(request, 'cases/reports_dashboard.html', context)
