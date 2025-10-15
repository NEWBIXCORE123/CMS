from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "certificates"

    def ready(self):
        # ✅ Import and run startup checks for template directory
        try:
            from .startup import ensure_certificate_templates
            ensure_certificate_templates()
        except Exception as e:
            # Avoid breaking startup if something minor fails
            print(f"[Startup Warning] Could not ensure certificate templates: {e}")
