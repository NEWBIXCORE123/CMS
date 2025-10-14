# cms/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from certificates.views.auth_views import landing_page  # import directly from auth_views

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # Root → Landing Page
    path('', landing_page, name='landing_page'),

    # Certificates app (handles all auth + dashboard routes)
    path('certificates/', include(('certificates.urls', 'certificates'), namespace='certificates')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
