from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Firm

class FirmListView(LoginRequiredMixin, ListView):
    model = Firm
    template_name = "firms/firm_list.html"

class FirmDetailView(LoginRequiredMixin, DetailView):
    model = Firm
    template_name = "firms/firm_detail.html"
    context_object_name = 'firm'

class FirmCreateView(LoginRequiredMixin, CreateView):
    model = Firm
    fields = '__all__'
    template_name = "firms/firm_create.html"
    success_url = reverse_lazy('firm_list')

class FirmUpdateView(LoginRequiredMixin, UpdateView):
    model = Firm
    fields = '__all__'
    template_name = "firms/firm_update.html"
    success_url = reverse_lazy('firm_list')
