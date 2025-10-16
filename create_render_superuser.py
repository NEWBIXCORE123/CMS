import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brgy_cms.settings")
django.setup()

from django.contrib.auth.models import User

# 🔐 Customize your admin account details
username = "admin"
email = "admin@example.com"
password = "admin123"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("✅ Render Superuser created successfully!")
else:
    print("⚠️ Render Superuser already exists.")
