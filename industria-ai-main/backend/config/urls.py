from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    index_view,
    login_page,
    engineer_dashboard_page,
    admin_dashboard_page,
    supervisor_dashboard_page
)

urlpatterns = [
    # Administration
    path('admin/', admin.site.urls),

    # Frontend Page Views
    path('', index_view, name='index'),
    path('login/', login_page, name='login_page'),
    path('engineer/', engineer_dashboard_page, name='engineer_dashboard_page'),
    path('admin-dashboard/', admin_dashboard_page, name='admin_dashboard_page'),
    path('supervisor/', supervisor_dashboard_page, name='supervisor_dashboard_page'),

    # REST APIs
    path('api/auth/', include('accounts.urls')),
    path('api/machines/', include('machines.urls')),
    path('api/manuals/', include('manuals.urls')),
    path('api/assistant/', include('assistant.urls')),
    path('api/supervisor/', include('history.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
