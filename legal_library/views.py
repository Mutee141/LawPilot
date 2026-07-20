from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Judgment, Justice


def can_access_legal_library(user):
    return user.is_authenticated and user.role in ['firm_owner', 'system_admin', 'senior_lawyer']


def legal_library_access_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not can_access_legal_library(request.user):
            messages.error(request, 'You do not have permission to access the Legal Library.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@legal_library_access_required
def judgments_list(request):
    justices = Justice.objects.all().order_by('name')
    judgments = Judgment.objects.select_related('justice', 'uploaded_by').order_by('-uploaded_at')

    current_justice = None
    justice_id = request.GET.get('justice')
    query = request.GET.get('q', '').strip()

    if justice_id:
        current_justice = get_object_or_404(Justice, id=justice_id)
        judgments = judgments.filter(justice=current_justice)

    if query:
        judgments = judgments.filter(
            Q(title__icontains=query) |
            Q(case_number__icontains=query) |
            Q(justice__name__icontains=query)
        )

    context = {
        'justices': justices,
        'judgments': judgments,
        'current_justice': current_justice,
        'query': query,
    }
    return render(request, 'legal_library/judgments.html', context)


@legal_library_access_required
def judgment_detail(request, pk):
    judgment = get_object_or_404(Judgment, pk=pk)
    return render(request, 'legal_library/judgment_detail.html', {'judgment': judgment})


@legal_library_access_required
def acts_list(request):
    return render(request, 'legal_library/placeholder_library.html', {
        'title': 'Acts',
        'description': 'Acts library content will be added here.'
    })


@legal_library_access_required
def sections_list(request):
    return render(request, 'legal_library/placeholder_library.html', {
        'title': 'Sections',
        'description': 'Sections library content will be added here.'
    })


@legal_library_access_required
def case_laws_list(request):
    return render(request, 'legal_library/placeholder_library.html', {
        'title': 'Case Laws',
        'description': 'Case laws library content will be added here.'
    })


@legal_library_access_required
def ai_search(request):
    return render(request, 'legal_library/placeholder_library.html', {
        'title': 'AI Search',
        'description': 'AI search results will be added here.'
    })
