from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from cases.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('cases/', include('cases.urls')),
    path('firms/', include('firms.urls')),
    path('legal_library/', include('legal_library.urls')),
    path('', RedirectView.as_view(pattern_name='login'), name='home_redirect'),
]

# Always serve media files (needed for production on Render)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)