# cms/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from certificates.views.auth_views import landing_page
from django.http import HttpResponse
from django.contrib.auth.models import User

# ----------------------------
# Temporary route: create admin
# ----------------------------
def create_admin(request):
    username = "superadmin"
    email = "superadmin@example.com"
    password = "admin123"

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        return HttpResponse("✅ Superuser created successfully on Render PostgreSQL DB!")
    else:
        return HttpResponse("⚠️ Superuser already exists on Render DB.")

# ----------------------------
# URL patterns
# ----------------------------
urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # Temporary admin creation route
    path('create-admin/', create_admin, name='create_admin'),

    # Root → Landing Page
    path('', landing_page, name='landing_page'),

    # Certificates app (handles all auth + dashboard routes)
    path('certificates/', include(('certificates.urls', 'certificates'), namespace='certificates')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
