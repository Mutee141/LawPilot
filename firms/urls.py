from django.urls import path
from .views import *

urlpatterns = [
    path('', FirmListView.as_view(), name='firm_list'),
    path('<uuid:pk>/', FirmDetailView.as_view(), name='firm_detail'),
    path('create/', FirmCreateView.as_view(), name='firm_create'),
    path('<uuid:pk>/update/', FirmUpdateView.as_view(), name='firm_update'),
]
