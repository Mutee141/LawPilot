from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Prefetch, Q, Count
from django.http import HttpResponse
from datetime import datetime, date, timedelta

from .models import Case, CaseActivity, Hearing
from accounts.models import User
import csv
import openpyxl
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def check_report_permission(user, report_name):
    if user.role == 'junior_lawyer':
        return False
    if user.role == 'senior_lawyer' and report_name not in ['case_history', 'lawyer_workload']:
        return False
    return True


@login_required
def reports_index(request):
    if not check_report_permission(request.user, 'case_history'):
        messages.error(request, "You do not have permission to view reports.")
        return redirect('dashboard_redirect')
    return redirect('report_case_history')


@login_required
def report_case_history(request):
    if not check_report_permission(request.user, 'case_history'):
        return redirect('dashboard_redirect')
    
    user = request.user
    if user.role == 'firm_owner':
        cases_qs = Case.objects.filter(firm=user.firm)
    else:
        cases_qs = Case.objects.filter(
            Q(owner=user) | 
            Q(assigned_senior_lawyer=user) | 
            Q(assigned_lawyers=user)
        ).filter(firm=user.firm).distinct()
        
    activities_prefetch = Prefetch(
        'activities',
        queryset=CaseActivity.objects.order_by('-timestamp')
    )
    cases_with_history = cases_qs.prefetch_related(activities_prefetch, 'assigned_lawyers', 'assigned_senior_lawyer', 'client').order_by('-created_at')
    
    context = {
        'active_report': 'case_history',
        'cases': cases_with_history,
    }
    return render(request, 'cases/reports/case_history.html', context)


@login_required
def report_monthly_filing(request):
    if not check_report_permission(request.user, 'monthly_filing'):
        return redirect('dashboard_redirect')
        
    user = request.user
    cases_qs = Case.objects.filter(firm=user.firm).prefetch_related('assigned_lawyers', 'assigned_senior_lawyer')
    
    monthly_cases = {}
    for c in cases_qs:
        dt = c.filing_date if c.filing_date else c.created_at.date()
        if dt:
            month_key = dt.strftime('%B %Y')
            if month_key not in monthly_cases:
                monthly_cases[month_key] = []
            monthly_cases[month_key].append(c)
            
    # Sort by month (descending order approximate by taking first case's date)
    sorted_monthly_cases = sorted(monthly_cases.items(), key=lambda x: x[1][0].filing_date if x[1][0].filing_date else x[1][0].created_at.date(), reverse=True)
    
    context = {
        'active_report': 'monthly_filing',
        'monthly_cases': sorted_monthly_cases,
    }
    return render(request, 'cases/reports/monthly_filing.html', context)


@login_required
def report_lawyer_workload(request):
    if not check_report_permission(request.user, 'lawyer_workload'):
        return redirect('dashboard_redirect')
        
    user = request.user
    
    if user.role == 'firm_owner':
        users = User.objects.filter(firm=user.firm).order_by('role', 'first_name')
    else:
        users = User.objects.filter(id=user.id) # Only see their own
        
    user_case_stats = []
    for u in users:
        base_qs = Case.objects.filter(firm=user.firm).filter(
            Q(owner=u) | 
            Q(assigned_senior_lawyer=u) | 
            Q(assigned_lawyers=u)
        ).distinct()
        
        active_count = base_qs.exclude(status__in=['closed', 'decided']).count()
        closed_count = base_qs.filter(status__in=['closed', 'decided']).count()
        
        user_case_stats.append({
            'user': u,
            'role': u.get_role_display(),
            'active_cases': active_count,
            'closed_cases': closed_count
        })
        
    context = {
        'active_report': 'lawyer_workload',
        'user_case_stats': user_case_stats,
    }
    return render(request, 'cases/reports/lawyer_workload.html', context)


@login_required
def report_case_status(request):
    if not check_report_permission(request.user, 'case_status'):
        return redirect('dashboard_redirect')
        
    user = request.user
    cases_qs = Case.objects.filter(firm=user.firm)
    
    status_counts = cases_qs.values('status').annotate(count=Count('status')).order_by('-count')
    
    # Map status codes to display values
    status_display = dict(Case.STATUS_CHOICES)
    formatted_counts = []
    for sc in status_counts:
        formatted_counts.append({
            'status': status_display.get(sc['status'], sc['status']).title(),
            'count': sc['count']
        })
        
    context = {
        'active_report': 'case_status',
        'status_counts': formatted_counts,
    }
    return render(request, 'cases/reports/case_status.html', context)


@login_required
def report_hearings(request):
    if not check_report_permission(request.user, 'hearings'):
        return redirect('dashboard_redirect')
        
    user = request.user
    today = date.today()
    
    # We'll get all hearings for cases belonging to the firm
    hearings_qs = Hearing.objects.filter(case__firm=user.firm).select_related('case', 'case__assigned_senior_lawyer').order_by('hearing_date')
    
    upcoming = hearings_qs.filter(hearing_date__gte=today)
    completed = hearings_qs.filter(hearing_date__lt=today, hearing_outcome__isnull=False).exclude(hearing_outcome='')
    missed = hearings_qs.filter(hearing_date__lt=today).filter(Q(hearing_outcome__isnull=True) | Q(hearing_outcome=''))
    
    context = {
        'active_report': 'hearings',
        'upcoming_hearings': upcoming,
        'completed_hearings': completed,
        'missed_hearings': missed,
    }
    return render(request, 'cases/reports/hearings.html', context)


@login_required
def export_report(request, report_type, format_type):
    if not check_report_permission(request.user, report_type):
        return HttpResponse("Unauthorized", status=403)
        
    user = request.user
    title = f"{report_type.replace('_', ' ').title()} Report"
    
    # Prepare data based on report type
    headers = []
    data = []
    
    if report_type == 'case_history':
        headers = ['Case Number', 'Title', 'Client', 'Status', 'Filing Date']
        if user.role == 'firm_owner':
            cases_qs = Case.objects.filter(firm=user.firm)
        else:
            cases_qs = Case.objects.filter(Q(owner=user) | Q(assigned_senior_lawyer=user) | Q(assigned_lawyers=user)).filter(firm=user.firm).distinct()
        for c in cases_qs.order_by('-created_at'):
            data.append([
                c.case_number or '-',
                c.title or 'Untitled',
                c.client.full_name if c.client else '-',
                c.get_status_display(),
                str(c.filing_date or c.created_at.date())
            ])
            
    elif report_type == 'monthly_filing':
        headers = ['Month', 'Case Name', 'Assigned Senior', 'Filing Date']
        cases_qs = Case.objects.filter(firm=user.firm).prefetch_related('assigned_senior_lawyer')
        for c in cases_qs:
            dt = c.filing_date or c.created_at.date()
            if dt:
                data.append([
                    dt.strftime('%B %Y'),
                    c.title or 'Untitled',
                    c.assigned_senior_lawyer.get_full_name() if c.assigned_senior_lawyer else '-',
                    str(dt)
                ])
                
    elif report_type == 'lawyer_workload':
        headers = ['Lawyer Name', 'Role', 'Active Cases', 'Closed Cases']
        if user.role == 'firm_owner':
            users = User.objects.filter(firm=user.firm)
        else:
            users = User.objects.filter(id=user.id)
            
        for u in users:
            base_qs = Case.objects.filter(firm=user.firm).filter(Q(owner=u) | Q(assigned_senior_lawyer=u) | Q(assigned_lawyers=u)).distinct()
            active = base_qs.exclude(status__in=['closed', 'decided']).count()
            closed = base_qs.filter(status__in=['closed', 'decided']).count()
            data.append([u.get_full_name() or u.username, u.get_role_display(), str(active), str(closed)])
            
    elif report_type == 'case_status':
        headers = ['Status', 'Count']
        cases_qs = Case.objects.filter(firm=user.firm)
        status_counts = cases_qs.values('status').annotate(count=Count('status')).order_by('-count')
        status_display = dict(Case.STATUS_CHOICES)
        for sc in status_counts:
            data.append([status_display.get(sc['status'], sc['status']).title(), str(sc['count'])])
            
    elif report_type == 'hearings':
        headers = ['Date', 'Case', 'Senior Lawyer', 'Outcome']
        hearings_qs = Hearing.objects.filter(case__firm=user.firm).select_related('case', 'case__assigned_senior_lawyer').order_by('hearing_date')
        for h in hearings_qs:
            data.append([
                str(h.hearing_date),
                h.case.title or '-',
                h.case.assigned_senior_lawyer.get_full_name() if h.case.assigned_senior_lawyer else '-',
                h.hearing_outcome or 'Pending'
            ])
            
    if not data:
        data.append(["No data available" for _ in headers])

    if format_type == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.append(headers)
        for row in data:
            ws.append(row)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={report_type}_report.xlsx'
        wb.save(response)
        return response
        
    elif format_type == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={report_type}_report.pdf'
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 20))
        
        table_data = [headers] + data
        # Calculate col widths (distribute evenly)
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b5ae4')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('TOPPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0'))
        ]))
        elements.append(t)
        doc.build(elements)
        return response

    return HttpResponse("Invalid format", status=400)
