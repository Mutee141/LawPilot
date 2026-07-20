from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from cases.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('cases/', include('cases.urls')),
    path('firms/', include('firms.urls')),
    path('legal_library/', include('legal_library.urls')),
    path('', RedirectView.as_view(pattern_name='login'), name='home_redirect'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)