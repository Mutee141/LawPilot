from django.urls import reverse_lazy
from django.views import generic
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import logout
from .forms import LawyerSignupForm, TaskAssignmentForm
from .models import User
from firms.models import Firm
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from cases.models import Case, Task, CaseActivity, Hearing, Invoice, Client, Court
from .models import User
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from calendar import monthrange
import calendar
from django.contrib import messages
from django.http import JsonResponse
import json


class SignUpView(generic.CreateView):
    form_class = LawyerSignupForm
    template_name = 'accounts/signup.html'
    
    def get_success_url(self):
        # After signup, redirect to firm setup
        return reverse_lazy('firm_setup')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        return response

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):

        user = self.request.user

        if user.role == "client":
            return reverse_lazy("client_dashboard")

        elif user.role == "senior_lawyer":
            return reverse_lazy("senior_dashboard")

        elif user.role == "junior_lawyer":
            return reverse_lazy("junior_dashboard")

        elif user.role == "accountant":
            return reverse_lazy("accountant_dashboard")

        elif user.role == "firm_owner":
            return reverse_lazy("owner_dashboard")

        elif user.role == "system_admin":
            return reverse_lazy("system_admin_dashboard")

        return reverse_lazy("dashboard_redirect")


@login_required
def firm_setup(request):
    """Redirect users to firm setup if they don't have a firm"""
    user = request.user
    
    # If user already has a firm, redirect to dashboard
    if user.firm:
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_firm':
            # Create new firm
            firm_name = request.POST.get('firm_name', '').strip()
            firm_email = request.POST.get('firm_email', '').strip()
            firm_phone = request.POST.get('firm_phone', '').strip()
            
            if firm_name:
                firm = Firm.objects.create(
                    name=firm_name,
                    email=firm_email,
                    phone=firm_phone,
                    is_active=True
                )
                user.firm = firm
                user.role = 'firm_owner'  # Auto-promote creator to firm_owner
                user.save()
                return redirect('dashboard_redirect')
        
        elif action == 'open_dialog':
            # Show create firm dialog
            pass
    
    # Check if there are any existing firms user can join
    existing_firms = Firm.objects.all()
    context = {
        'existing_firms': existing_firms,
    }
    
    return render(request, 'accounts/firm_setup.html', context)


@login_required
def join_firm(request, firm_id):
    """Allow users to join an existing firm"""
    user = request.user
    
    if user.firm:
        return redirect('dashboard_redirect')
    
    try:
        firm = Firm.objects.get(id=firm_id)
        user.firm = firm
        user.save()
        return redirect('dashboard_redirect')
    except Firm.DoesNotExist:
        return redirect('firm_setup')


@login_required
def dashboard_redirect(request):
    user = request.user

    if user.role == 'system_admin':
        return redirect('system_admin_dashboard')

    # If no firm → setup
    if not user.firm:
        return redirect('firm_setup')

    # Client
    if user.role == 'client':
        return redirect('client_dashboard')

    # Senior
    if user.role == 'senior_lawyer':
        return redirect('senior_dashboard')

    # Junior
    if user.role == 'junior_lawyer':
        return redirect('junior_dashboard')

    # Firm Owner
    if user.role == 'firm_owner':
        return redirect('owner_dashboard')

    # Accountant
    if user.role == 'accountant':
        return redirect('accountant_dashboard')

    # Fallback
    return redirect('dashboard_redirect')


@login_required
def system_admin_dashboard(request):
    if request.user.role != 'system_admin' and not request.user.is_superuser:
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        firm_name = request.POST.get('firm_name')
        registration = request.POST.get('registration_number')
        
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        cnic_no = request.POST.get('cnic_no')
        ntn_no = request.POST.get('ntn_no')
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        email = request.POST.get('email')
        confirm_email = request.POST.get('confirm_email')
        mobile_no = request.POST.get('mobile_no')
        landline_no = request.POST.get('landline_no')
        
        country = request.POST.get('country')
        province = request.POST.get('province')
        city = request.POST.get('city')
        secret_question = request.POST.get('secret_question')
        secret_answer = request.POST.get('secret_answer')
        address = request.POST.get('address')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('system_admin_dashboard')
            
        if email != confirm_email:
            messages.error(request, "Emails do not match.")
            return redirect('system_admin_dashboard')
            
        if username and User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('system_admin_dashboard')

        if firm_name and username and password:
            firm = Firm.objects.create(
                name=firm_name,
                registration_number=registration,
                email=email,
                phone=mobile_no,
                address=address,
                is_active=True
            )
            
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=mobile_no,
                firm=firm,
                role='firm_owner',
                gender=gender,
                cnic_no=cnic_no,
                ntn_no=ntn_no,
                landline_no=landline_no,
                country=country,
                province=province,
                city=city,
                secret_question=secret_question,
                secret_answer=secret_answer,
                address=address
            )
            messages.success(request, f"Firm '{firm_name}' and Owner '{username}' created successfully.")
            return redirect('system_admin_dashboard')
            
    firms = Firm.objects.prefetch_related('users').all().order_by('-created_at')
    all_employees = User.objects.exclude(role='system_admin').select_related('firm').order_by('firm__name', 'username')
    
    from cases.models import Case
    import json
    
    # 1. Firms Registered Per Month
    monthly_firms = {}
    for f in firms:
        if f.created_at:
            sort_key = f.created_at.strftime('%Y-%m')
            display_label = f.created_at.strftime('%B %Y')
            m = (sort_key, display_label)
        else:
            m = ('Unknown', 'Unknown')
        monthly_firms[m] = monthly_firms.get(m, 0) + 1
        
    sorted_firm_keys = sorted(list(monthly_firms.keys()), key=lambda x: x[0])
    firm_months_labels = json.dumps([k[1] for k in sorted_firm_keys])
    firm_months_counts = json.dumps([monthly_firms[k] for k in sorted_firm_keys])

    # 2 & 3. Cases and Users per firm
    firm_names = json.dumps([f.name for f in firms])
    firm_users_counts = json.dumps([f.users.count() for f in firms])
    firm_cases_counts = json.dumps([Case.objects.filter(firm=f).count() for f in firms])
    
    context = {
        'firms': firms,
        'total_firms': firms.count(),
        'active_firms': firms.filter(is_active=True).count(),
        'all_employees': all_employees,
        'courts': Court.objects.all(),
        'firm_months_labels': firm_months_labels,
        'firm_months_counts': firm_months_counts,
        'firm_names': firm_names,
        'firm_users_counts': firm_users_counts,
        'firm_cases_counts': firm_cases_counts,
    }
    return render(request, 'dashboard/admin.html', context)

@login_required
def system_admin_create_owner(request):
    """System admin creates firm and owner."""
    if request.user.role != 'system_admin' and not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        firm_name = request.POST.get('firm_name')
        registration = request.POST.get('registration_number')
        
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        cnic_no = request.POST.get('cnic_no')
        ntn_no = request.POST.get('ntn_no')
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        email = request.POST.get('email')
        confirm_email = request.POST.get('confirm_email')
        mobile_no = request.POST.get('mobile_no')
        landline_no = request.POST.get('landline_no')
        
        country = request.POST.get('country')
        province = request.POST.get('province')
        city = request.POST.get('city')
        secret_question = request.POST.get('secret_question')
        secret_answer = request.POST.get('secret_answer')
        address = request.POST.get('address')
        
        errors = []
        if password != confirm_password: errors.append("Passwords do not match.")
        if email != confirm_email: errors.append("Emails do not match.")
        if username and User.objects.filter(username=username).exists():
            errors.append("Username is already taken.")
            
        if not errors and firm_name and username and password:
            try:
                firm = Firm.objects.create(
                    name=firm_name,
                    registration_number=registration,
                    email=email,
                    phone=mobile_no,
                    address=address,
                    is_active=True
                )
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=mobile_no,
                    firm=firm,
                    role='firm_owner',
                    gender=gender,
                    cnic_no=cnic_no,
                    ntn_no=ntn_no,
                    landline_no=landline_no,
                    country=country,
                    province=province,
                    city=city,
                    secret_question=secret_question,
                    secret_answer=secret_answer,
                    address=address
                )
                messages.success(request, f"Firm '{firm_name}' and Owner '{username}' created successfully.")
                return redirect('system_admin_dashboard')
            except Exception as e:
                errors.append(str(e))
                
        context = {
            'errors': errors,
            'form_data': request.POST
        }
        return render(request, 'accounts/create_firm_owner.html', context)
        
    return render(request, 'accounts/create_firm_owner.html')

@login_required
def system_manage_firms(request):
    """System admin view to manage all firms"""
    if request.user.role != 'system_admin' and not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    firms = Firm.objects.all().order_by('-created_at')
    context = {'firms': firms}
    return render(request, 'accounts/system_manage_firms.html', context)

@login_required
def system_firm_details_list(request):
    """System admin view to show detailed information of all firms."""
    if request.user.role != 'system_admin' and not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    firms = Firm.objects.prefetch_related('users').all().order_by('-created_at')
    
    firm_details = []
    for firm in firms:
        owner = firm.users.filter(role='firm_owner').first()
        firm_details.append({
            'firm': firm,
            'owner': owner
        })
        
    context = {'firm_details': firm_details}
    return render(request, 'accounts/system_firm_details.html', context)

@login_required
def toggle_firm_status(request, pk):
    """Toggle firm active status (System Admin)"""
    if request.user.role != 'system_admin' and not request.user.is_superuser:
        return redirect('dashboard_redirect')
        
    firm_to_toggle = get_object_or_404(Firm, pk=pk)
    
    if request.method == 'POST':
        firm_to_toggle.is_active = not firm_to_toggle.is_active
        firm_to_toggle.save()
        
        # Also toggle all users in the firm
        User.objects.filter(firm=firm_to_toggle).update(is_active=firm_to_toggle.is_active)
        
        status_text = "activated" if firm_to_toggle.is_active else "deactivated"
        messages.success(request, f"Firm '{firm_to_toggle.name}' has been {status_text}.")
        
    return redirect(request.META.get('HTTP_REFERER', 'system_manage_firms'))

# ===================== STAFF MANAGEMENT =====================

class FirmOwnerRequiredMixin(UserPassesTestMixin):
    """Only firm owners can access staff management"""
    def test_func(self):
        return self.request.user.role == 'firm_owner'


@login_required
def staff_list(request):
    """List all staff and clients in the firm"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    staff = User.objects.filter(firm=request.user.firm).order_by('role', 'first_name')
    employees = staff.exclude(role='client')
    clients = staff.filter(role='client')
    
    context = {
        'employees': employees,
        'clients': clients
    }
    return render(request, 'accounts/staff_list.html', context)


@login_required
def staff_create(request):
    """Create new staff member"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        # Handle staff creation
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'junior_lawyer').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Validation
        errors = []
        if not username:
            errors.append('Username is required')
        if not email:
            errors.append('Email is required')
        if not role:
            errors.append('Role is required')
        if not password:
            errors.append('Password is required')
        
        # Check if username already exists
        if username and User.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" is already taken')
        
        if errors:
            context = {
                'roles': User.ROLE_CHOICES,
                'errors': errors,
                'form_data': {
                    'username': username,
                    'email': email,
                    'role': role,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                }
            }
            return render(request, 'accounts/staff_form.html', context)
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                firm=request.user.firm,
                role=role
            )
            messages.success(request, f"User {username} added successfully.")
            return redirect('owner_dashboard')
        except Exception as e:
            errors.append(f"Database/Validation Error: {str(e)}")
            context = {
                'roles': User.ROLE_CHOICES,
                'errors': errors,
                'form_data': {
                    'username': username,
                    'email': email,
                    'role': role,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                }
            }
            return render(request, 'accounts/staff_form.html', context)
    
    context = {'roles': User.ROLE_CHOICES}
    return render(request, 'accounts/staff_form.html', context)


@login_required
def staff_update(request, pk):
    """Update staff information"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    user = get_object_or_404(User, pk=pk, firm=request.user.firm)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        
        # Validation
        errors = []
        if not email:
            errors.append('Email is required')
        if not role:
            errors.append('Role is required')
        
        if errors:
            context = {
                'staff_member': user,
                'roles': User.ROLE_CHOICES,
                'errors': errors,
            }
            return render(request, 'accounts/staff_form.html', context)
        
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.role = role
        user.phone_number = phone_number
        user.save()
        messages.success(request, f"User {user.username} updated successfully.")
        return redirect('owner_dashboard')
    
    context = {'staff_member': user, 'roles': User.ROLE_CHOICES}
    return render(request, 'accounts/staff_form.html', context)


@login_required
def staff_reset_password(request, pk):
    """Firm owner can reset passwords for staff"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
        
    user = get_object_or_404(User, pk=pk, firm=request.user.firm)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
            user.save()
            messages.success(request, f"Password for {user.username} has been updated successfully.")
        else:
            messages.error(request, "Password cannot be empty.")
        return redirect('owner_dashboard')
        
    return redirect('owner_dashboard')


@login_required
def staff_delete(request, pk):
    """Delete staff member"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    user = get_object_or_404(User, pk=pk, firm=request.user.firm)
    
    if request.method == 'POST':
        user.delete()
        return redirect('staff_list')
    
    context = {'object': user}
    return render(request, 'accounts/staff_confirm_delete.html', context)


@login_required
def toggle_user_status(request, pk):
    """Toggle user active status"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
        
    user_to_toggle = get_object_or_404(User, pk=pk, firm=request.user.firm)
    
    if user_to_toggle == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        if request.method == 'POST':
            user_to_toggle.is_active = not user_to_toggle.is_active
            user_to_toggle.save()
            status_text = "activated" if user_to_toggle.is_active else "deactivated"
            messages.success(request, f"User {user_to_toggle.username} has been {status_text}.")
            
    return redirect(request.META.get('HTTP_REFERER', 'owner_dashboard'))


# ===================== PROFILE & SETTINGS =====================

@login_required
def profile(request):
    """User profile page"""
    user = request.user
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        
        errors = []
        if not first_name:
            errors.append('First name is required')
        if not email:
            errors.append('Email is required')
        
        # Check if email already used by another user
        if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            errors.append('This email is already in use')
        
        if errors:
            context = {
                'user': user,
                'errors': errors,
            }
            return render(request, 'accounts/profile.html', context)
        
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone_number = phone_number
        user.save()
        
        context = {
            'user': user,
            'success': True,
            'message': 'Profile updated successfully!'
        }
        return render(request, 'accounts/profile.html', context)
    
    context = {'user': user}
    return render(request, 'accounts/profile.html', context)


@login_required
def settings(request):
    """Firm settings page"""
    user = request.user
    firm = user.firm
    
    if request.method == 'POST':
        if user.role != 'firm_owner':
            return redirect('dashboard_redirect')
        
        firm_name = request.POST.get('firm_name', '').strip()
        firm_email = request.POST.get('firm_email', '').strip()
        firm_phone = request.POST.get('firm_phone', '').strip()
        address = request.POST.get('address', '').strip()
        
        errors = []
        if not firm_name:
            errors.append('Firm name is required')
        
        if errors:
            context = {
                'firm': firm,
                'errors': errors,
            }
            return render(request, 'accounts/settings.html', context)
        
        firm.name = firm_name
        firm.email = firm_email
        firm.phone = firm_phone
        firm.address = address
        firm.save()
        
        context = {
            'firm': firm,
            'success': True,
            'message': 'Settings updated successfully!'
        }
        return render(request, 'accounts/settings.html', context)
    
    context = {'firm': firm}
    return render(request, 'accounts/settings.html', context)


@login_required
def manage_firms(request):
    """Manage all firms (for firm owner)"""
    # Only super admin or system admin should see this in production
    # For now, firm owners can manage their own firm via settings
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    firms = Firm.objects.all() if request.user.is_superuser else Firm.objects.filter(id=request.user.firm_id)
    context = {'firms': firms}
    return render(request, 'accounts/manage_firms.html', context)


@login_required
def user_accounts(request):
    """Manage all user accounts in the firm"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    # Get all users in the firm
    users = User.objects.filter(firm=request.user.firm)
    context = {
        'users': users,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'accounts/user_accounts.html', context)


@login_required
def manage_roles(request):
    """Manage user roles"""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip()
        new_role = request.POST.get('role', '').strip()
        
        try:
            user = User.objects.get(pk=user_id, firm=request.user.firm)
            
            # Prevent removing the only firm owner
            if user.role == 'firm_owner' and new_role != 'firm_owner':
                firm_owners = User.objects.filter(firm=request.user.firm, role='firm_owner')
                if firm_owners.count() == 1:
                    context = {
                        'users': User.objects.filter(firm=request.user.firm),
                        'role_choices': User.ROLE_CHOICES,
                        'error': 'Cannot remove the last firm owner. Assign another owner first.'
                    }
                    return render(request, 'accounts/manage_roles.html', context)
            
            user.role = new_role
            user.save()
            
            context = {
                'users': User.objects.filter(firm=request.user.firm),
                'role_choices': User.ROLE_CHOICES,
                'success': f'{user.get_full_name()} role updated to {user.get_role_display()}'
            }
            return render(request, 'accounts/manage_roles.html', context)
        except User.DoesNotExist:
            pass
    
    users = User.objects.filter(firm=request.user.firm)
    context = {
        'users': users,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'accounts/manage_roles.html', context)

@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')


@login_required
def owner_dashboard(request):
    """Firm owner dashboard focused exclusively on User and Firm management."""
    firm = request.user.firm
    
    # Check permission
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')

    # Get all staff
    staff = User.objects.filter(firm=firm).order_by('role', 'first_name')
    employees = staff.exclude(role='client')
    clients = staff.filter(role='client')
    
    total_staff = employees.count()
    senior_count = employees.filter(role='senior_lawyer').count()
    junior_count = employees.filter(role='junior_lawyer').count()
    active_staff_count = employees.filter(is_active=True).count()
    
    from cases.models import Case
    import json
    
    # Firm-level case stats
    all_cases = Case.objects.filter(firm=firm)
    total_cases = all_cases.count()
    
    # Monthly cases and status data
    monthly_data = {}
    status_data = {}
    for c in all_cases:
        if c.created_at:
            sort_key = c.created_at.strftime('%Y-%m')
            display_label = c.created_at.strftime('%B %Y')
            m = (sort_key, display_label)
        else:
            m = ('Unknown', 'Unknown')
        monthly_data[m] = monthly_data.get(m, 0) + 1
        s = c.get_status_display()
        status_data[s] = status_data.get(s, 0) + 1
        
    sorted_keys = sorted(list(monthly_data.keys()), key=lambda x: x[0])
    months_labels = [k[1] for k in sorted_keys]
    months_counts = [monthly_data[k] for k in sorted_keys]
    status_labels = list(status_data.keys())
    status_counts = [status_data[s] for s in status_labels]

    context = {
        "firm": firm,
        "employees": employees,
        "clients": clients,
        "total_staff": total_staff,
        "senior_count": senior_count,
        "junior_count": junior_count,
        "active_staff_count": active_staff_count,
        "total_cases": total_cases,
        "months_labels": json.dumps(months_labels),
        "months_counts": json.dumps(months_counts),
        "status_labels": json.dumps(status_labels),
        "status_counts": json.dumps(status_counts),
    }

    return render(request, "dashboard/owner_dashboard.html", context)


@login_required
def employee_bio_data(request):
    """View to show bio data of all users in the firm including the owner."""
    if request.user.role != 'firm_owner':
        return redirect('dashboard_redirect')
    
    firm = request.user.firm
    # Fetch all users in the firm, ordered by role and name
    all_users = User.objects.filter(firm=firm).order_by('role', 'first_name')
    
    context = {
        'firm': firm,
        'all_users': all_users,
    }
    return render(request, 'accounts/employee_bio_data.html', context)


@login_required
def senior_dashboard(request):

    user = request.user
    firm = user.firm
    now = timezone.now()
    today = now.date()


    juniors = User.objects.filter(
        firm=firm,
        role="junior_lawyer",
        managed_by=user
    )

    if not juniors.exists():
        juniors = User.objects.filter(
            firm=firm,
            role="junior_lawyer"
        )

    junior_ids = juniors.values_list("id", flat=True)

  
    my_cases_qs = Case.objects.filter(
        firm=firm
    ).filter(
        Q(assigned_lawyers=user) |
        Q(assigned_senior_lawyer=user) |
        Q(owner=user) |
        Q(assigned_lawyers__in=junior_ids)
    ).distinct()

    total_cases = my_cases_qs.count()

  
    end_date = today + timedelta(days=7)

    todays_hearings = Hearing.objects.filter(
        case__firm=firm
    ).filter(
        Q(case__assigned_lawyers=user) |
        Q(case__assigned_senior_lawyer=user) |
        Q(case__owner=user) |
        Q(case__assigned_lawyers__in=junior_ids)
    ).filter(
        Q(hearing_date__date=today) | Q(next_hearing_date__date=today)
    ).distinct()

    upcoming_hearings = Hearing.objects.filter(
        case__firm=firm
    ).filter(
        Q(case__assigned_lawyers=user) |
        Q(case__assigned_senior_lawyer=user) |
        Q(case__owner=user) |
        Q(case__assigned_lawyers__in=junior_ids)
    ).filter(
        Q(hearing_date__date__range=[today, end_date]) |
        Q(next_hearing_date__date__range=[today, end_date])
    ).distinct().order_by("hearing_date")

   
    junior_stats = []

    for junior in juniors:
        junior_stats.append({
            "name": junior.get_full_name() or junior.username,
            "cases": Case.objects.filter(firm=firm, assigned_lawyers=junior).count(),
            "tasks": Task.objects.filter(firm=firm, assigned_to=junior).count(),
            "overdue": Task.objects.filter(firm=firm, assigned_to=junior, status="overdue").count(),
        })

    
    current_month = today.month
    current_year = today.year
    month_days = monthrange(current_year, current_month)[1]

    # Calendar hearings - all hearings related to the cases without monthly filter
    calendar_hearings = Hearing.objects.filter(
        case__firm=firm
    ).filter(
        Q(case__assigned_lawyers=user) |
        Q(case__assigned_senior_lawyer=user) |
        Q(case__owner=user) |
        Q(case__assigned_lawyers__in=junior_ids)
    ).distinct().order_by("hearing_date")

    month_hearings = calendar_hearings.filter(
        Q(hearing_date__year=current_year, hearing_date__month=current_month) |
        Q(next_hearing_date__year=current_year, next_hearing_date__month=current_month)
    ).values_list("hearing_date__date", flat=True)

    month_hearing_dates = list(month_hearings)

    import json

    # Case Status Data
    status_data = {}
    for c in my_cases_qs:
        s = c.get_status_display()
        status_data[s] = status_data.get(s, 0) + 1
        
    cases_by_status_labels = json.dumps(list(status_data.keys()))
    cases_by_status_counts = json.dumps(list(status_data.values()))

    # Task Status Data
    my_tasks = Task.objects.filter(
        firm=firm
    ).filter(
        Q(assigned_to=user) | Q(assigned_to__in=junior_ids)
    )
    
    task_status_data = {}
    for t in my_tasks:
        s = t.get_status_display()
        task_status_data[s] = task_status_data.get(s, 0) + 1
        
    tasks_by_status_labels = json.dumps(list(task_status_data.keys()))
    tasks_by_status_counts = json.dumps(list(task_status_data.values()))

    context = {
        "total_cases": total_cases,
        "todays_hearings_count": todays_hearings.count(),
        "upcoming_hearings_count": upcoming_hearings.count(),
        "todays_hearings_list": todays_hearings,
        "upcoming_hearings": upcoming_hearings,
        "calendar_hearings": calendar_hearings,
        "team_size": juniors.count(),
        "team_members": junior_stats,
        "calendar_days": range(1, month_days + 1),
        "month_hearing_dates": month_hearing_dates,
        "today": today,
        "month_name": calendar.month_name[current_month],
        "year": current_year,
        "cases_by_status_labels": cases_by_status_labels,
        "cases_by_status_counts": cases_by_status_counts,
        "tasks_by_status_labels": tasks_by_status_labels,
        "tasks_by_status_counts": tasks_by_status_counts,
    }

    return render(request, "dashboard/senior_dashboard.html", context)


@login_required
def junior_dashboard(request):

    user = request.user
    firm = user.firm
    today = timezone.now()
    next_week = today + timedelta(days=7)

    my_cases = Case.objects.filter(
        firm=firm
    ).filter(
        Q(assigned_lawyers=user) |
        Q(owner=user)
    ).distinct()

    my_tasks = Task.objects.filter(
        firm=firm,
        assigned_to=user
    )

    upcoming_hearings = Hearing.objects.filter(
        case__firm=firm
    ).filter(
        Q(case__assigned_lawyers=user) |
        Q(case__owner=user)
    ).filter(
        Q(hearing_date__date__range=[today.date(), next_week.date()]) |
        Q(next_hearing_date__date__range=[today.date(), next_week.date()])
    ).distinct()

    # Calendar hearings for junior dashboard
    current_month = today.month
    current_year = today.year
    calendar_hearings = Hearing.objects.filter(
        case__firm=firm
    ).filter(
        Q(case__assigned_lawyers=user) |
        Q(case__owner=user)
    ).distinct().order_by("hearing_date")

    context = {
        "cases_count": my_cases.count(),
        "pending_tasks": my_tasks.filter(status="pending").count(),
        "overdue_tasks": my_tasks.filter(status="overdue").count(),
        "completed_tasks": my_tasks.filter(status="completed").count(),
        "upcoming_hearings": upcoming_hearings,
        "my_tasks": my_tasks.order_by('-created_at'),
        "calendar_hearings": calendar_hearings,
        "today": today,
        "month_name": calendar.month_name[current_month],
        "year": current_year,
    }

    return render(request, "dashboard/junior_dashboard.html", context)


@login_required
def assign_task(request):
    """Allow senior lawyers to assign tasks to junior lawyers"""
    if request.user.role not in ['senior_lawyer', 'firm_owner']:
        messages.error(request, 'You do not have permission to assign tasks.')
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = TaskAssignmentForm(request.user, request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.firm = request.user.firm
            task.created_by = request.user
            task.save()
            messages.success(request, f'Task "{task.title}" assigned successfully!')
            return redirect('senior_dashboard')
    else:
        form = TaskAssignmentForm(request.user)
    
    return render(request, 'dashboard/assign_task.html', {'form': form})


@login_required
def update_task_status(request, task_id):
    """Update task status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        task = Task.objects.get(id=task_id, assigned_to=request.user)
        
        # Parse JSON data
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status in ['pending', 'in_progress', 'completed']:
            task.status = new_status
            task.save()
            
            # Create activity log
            CaseActivity.objects.create(
                firm=task.firm,
                case=task.case,
                user=request.user,
                action=f"Updated task status to {task.get_status_display()}",
                note=f"Task: {task.title}"
            )
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status'})
            
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def accountant_dashboard(request):
    """Dashboard for accountants and firm owners - billing and financial management"""
    
    user = request.user
    firm = user.firm
    
    # Permission check - only accountants and firm owners can access
    if user.role not in ['accountant', 'firm_owner']:
        return redirect('dashboard_redirect')
    
    # Ensure user has a firm
    if not firm:
        return redirect('firm_setup')
    
    # Get all invoices for the firm
    invoices = Invoice.objects.filter(
        firm=firm
    ).select_related('client', 'case', 'created_by').order_by('-created_at')

    # ==========================
    # Financial Summary
    # ==========================

    total_invoiced = invoices.aggregate(
        total=Sum("amount")
    )["total"] or 0

    collected = invoices.filter(
        status="paid"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    outstanding = invoices.filter(
        status__in=["pending", "overdue"]
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    total_invoices = invoices.count()

    paid_invoices = invoices.filter(status="paid").count()
    pending_invoices = invoices.filter(status="pending").count()
    overdue_invoices = invoices.filter(status="overdue").count()
    draft_invoices = invoices.filter(status="draft").count()

    recent_invoices = invoices[:5]

    # ==========================
    # Client Payment Summary
    # ==========================

    client_payments = []

    clients = invoices.values(
        "client__id",
        "client__full_name"
    ).distinct()

    today = timezone.now().date()

    for client in clients:

        client_id = client["client__id"]
        client_name = client["client__full_name"]

        client_invoices = invoices.filter(client_id=client_id)

        total_client = client_invoices.aggregate(
            total=Sum("amount")
        )["total"] or 0

        paid_client = client_invoices.filter(
            status="paid"
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        outstanding_client = total_client - paid_client

        # Overdue calculation
        overdue_invoices_list = client_invoices.filter(
            status="overdue"
        ).order_by("due_date")
        
        if overdue_invoices_list.exists():
            overdue_invoice = overdue_invoices_list.first()
            days_overdue = (today - overdue_invoice.due_date).days
        else:
            days_overdue = None

        client_payments.append({
            "id": client_id,
            "name": client_name,
            "total_invoiced": float(total_client),
            "paid": float(paid_client),
            "outstanding": float(outstanding_client),
            "days_overdue": days_overdue,
        })

    # ==========================
    # Revenue Metrics
    # ==========================
    
    # Collection percentage
    collection_percentage = 0
    if total_invoiced > 0:
        collection_percentage = round((collected / total_invoiced) * 100, 2)

    context = {
        "total_invoiced": float(total_invoiced),
        "collected": float(collected),
        "outstanding": float(outstanding),
        "total_invoices": total_invoices,
        "paid_invoices": paid_invoices,
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices,
        "draft_invoices": draft_invoices,
        "recent_invoices": recent_invoices,
        "client_payments": client_payments,
        "collection_percentage": collection_percentage,
    }

    return render(
        request,
        "dashboard/accountant_dashboard.html",
        context
    )
    
    
    from django.contrib.auth.decorators import login_required
from cases.models import Case, Invoice, Hearing
from .decorators import client_required


@login_required
@client_required
def client_dashboard(request):

    user = request.user
    client = user.client_profile
    firm = client.firm

    # Client cases
    my_cases = Case.objects.filter(
        firm=firm,
        client=client
    )

    # Client invoices
    my_invoices = Invoice.objects.filter(
        firm=firm,
        client=client
    )

    # Upcoming hearings
    upcoming_hearings = Hearing.objects.filter(
        case__client=client,
        case__firm=firm
    )

    context = {
        "client": client,
        "cases": my_cases,
        "invoices": my_invoices,
        "hearings": upcoming_hearings,
    }

    return render(
        request,
        "client_portal/dashboard.html",
        context
    )