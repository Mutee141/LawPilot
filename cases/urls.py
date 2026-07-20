from django.urls import path
from . import views
from . import reports

urlpatterns = [
    # Cases (root of this include)
    path("", views.case_list, name="case_list"),
    path("history/", views.case_history_list, name="case_history_list"),
    path("history/upload/", views.case_history_upload, name="case_history_upload"),
    path("create/", views.case_create, name="case_create"),
    path("<uuid:pk>/", views.case_detail, name="case_detail"),
    path("<uuid:case_id>/documents/upload/", views.upload_document, name="document_upload"),
    path("documents/<int:doc_id>/delete/", views.delete_document, name="delete_document"),
    path("<uuid:pk>/update/", views.case_update, name="case_update"),
    path("<uuid:pk>/delete/", views.case_delete, name="case_delete"),
    
    # Clients
    path("clients/", views.client_list, name="client_list"),
    path("clients/create/", views.client_create, name="client_create"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    
    # Hearings
    path("hearings/", views.hearing_list, name="hearing_list"),
    path("hearings/create/", views.hearing_create, name="hearing_create"),
    path("hearings/<int:pk>/", views.hearing_detail, name="hearing_detail"),
    path("hearings/<int:pk>/edit/", views.hearing_edit, name="hearing_edit"),
    path("hearings/<int:pk>/delete/", views.hearing_delete, name="hearing_delete"),
    
    # Courts
    path("courts/", views.court_list, name="court_list"),
    path("courts/create/", views.court_create, name="court_create"),
    path("courts/<int:pk>/", views.court_detail, name="court_detail"),
    path("courts/<int:pk>/edit/", views.court_update, name="court_update"),
    path("courts/<int:pk>/delete/", views.court_delete, name="court_delete"),
    
    # Invoices
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/create/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("invoices/<int:pk>/mark-paid/", views.invoice_mark_paid, name="invoice_mark_paid"),
    
    # Case Orders
    path("orders/create/", views.order_create, name="order_create"),
    path(
    'orders/create/<int:hearing_id>/',
    views.create_case_order,
    name='create_case_order'
),
    
    # Role-based Case Order Views
    path('orders/senior/', views.case_order_list_senior, name='case_order_list_senior'),
    path('orders/junior/', views.case_order_list_junior, name='case_order_list_junior'),
    path('orders/client/', views.case_order_list_client, name='case_order_list_client'),
    path('orders/admin/', views.case_order_list_admin, name='case_order_list_admin'),
    
    path('orders/create-new/', views.case_order_create, name='case_order_create'),
    path('orders/create/<int:hearing_id>/', views.case_order_create, name='case_order_create_hearing'),
    path('orders/create/case/<int:case_id>/', views.case_order_create, name='case_order_create_case'),
    
    path('orders/<int:order_id>/', views.case_order_detail, name='case_order_detail'),
    path('orders/<int:order_id>/edit/', views.case_order_edit, name='case_order_edit'),
    path('orders/<int:order_id>/delete/', views.case_order_delete, name='case_order_delete'),

    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_update, name='task_update'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),

    # Reports
    path('reports/', reports.reports_index, name='reports_dashboard'),
    path('reports/case-history/', reports.report_case_history, name='report_case_history'),
    path('reports/monthly-filing/', reports.report_monthly_filing, name='report_monthly_filing'),
    path('reports/lawyer-workload/', reports.report_lawyer_workload, name='report_lawyer_workload'),
    path('reports/case-status/', reports.report_case_status, name='report_case_status'),
    path('reports/hearings/', reports.report_hearings, name='report_hearings'),
    path('reports/<str:report_type>/export/<str:format_type>/', reports.export_report, name='export_report'),
]
