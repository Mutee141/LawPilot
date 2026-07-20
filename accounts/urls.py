# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import CustomLoginView
from .views import owner_dashboard, accountant_dashboard, dashboard_redirect, client_dashboard, senior_dashboard, junior_dashboard, system_admin_dashboard, system_admin_create_owner

urlpatterns = [
    # Authentication
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', dashboard_redirect, name='dashboard_redirect'),
    
   
    path('firm-setup/', views.firm_setup, name='firm_setup'),
    path('join-firm/<uuid:firm_id>/', views.join_firm, name='join_firm'),
    
    
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    
    
    path('manage-firms/', views.manage_firms, name='manage_firms'),
    path('user-accounts/', views.user_accounts, name='user_accounts'),
    path('manage-roles/', views.manage_roles, name='manage_roles'),
    
   
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_update, name='staff_update'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),
    path('staff/<int:pk>/reset-password/', views.staff_reset_password, name='staff_reset_password'),
    path('staff/<int:pk>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('staff/bio-data/', views.employee_bio_data, name='employee_bio_data'),
    
    path("owner/dashboard/", owner_dashboard, name="owner_dashboard"),
    path(
        "accountant/dashboard/",
        accountant_dashboard,
        name="accountant_dashboard"
    ),
    path(
    "client/dashboard/",
    client_dashboard,
    name="client_dashboard"
),
    path(
    "senior/dashboard/",
    senior_dashboard,
    name="senior_dashboard"
),
    path(
    "junior/dashboard/",
    junior_dashboard,
    name="junior_dashboard"
),
    path(
    "system-admin/dashboard/",
    system_admin_dashboard,
    name="system_admin_dashboard"
),
    path(
    "system-admin/create-owner/",
    system_admin_create_owner,
    name="system_admin_create_owner"
),
    path(
    "system-admin/manage-firms/",
    views.system_manage_firms,
    name="system_manage_firms"
),
    path(
    "system-admin/firm-details/",
    views.system_firm_details_list,
    name="system_firm_details_list"
),
    path(
    "system-admin/firms/<uuid:pk>/toggle-status/",
    views.toggle_firm_status,
    name="toggle_firm_status"
),
    
    # Task Management
    path('assign-task/', views.assign_task, name='assign_task'),
    path('tasks/<int:task_id>/update-status/', views.update_task_status, name='update_task_status'),
    
]
