from django.urls import path

from . import views

app_name = 'legal_library'

urlpatterns = [
    path('', views.judgments_list, name='judgments_list'),
    path('acts/', views.acts_list, name='acts_list'),
    path('sections/', views.sections_list, name='sections_list'),
    path('case-laws/', views.case_laws_list, name='case_laws_list'),
    path('ai-search/', views.ai_search, name='ai_search'),
    path('<int:pk>/', views.judgment_detail, name='judgment_detail'),
]
