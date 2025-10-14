from django.contrib import admin
from .models import Certificate, ActivityLog, AdminSignature, CertificateTemplate, ReissueLog


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "unique_id",
        "full_name",
        "document_type",
        "status",
        "created_at",
        "reissue_date",
        "reissued",
    )
    search_fields = ("unique_id", "full_name", "purpose", "address", "occupation")
    list_filter = ("document_type", "status", "reissued")
    readonly_fields = ("unique_id", "created_at", "verification_token")

    fieldsets = (
        ("Certificate Details", {
            "fields": (
                "unique_id",
                "full_name",
                "address",
                "age",
                "occupation",
                "purpose",
                "resident_since",
                "document_type",
                "status",
            ),
        }),
        ("Files", {
            "fields": ("generated_docx", "generated_pdf"),
        }),
        ("Dates", {
            "fields": ("created_at", "reissue_date", "expiration_date"),
        }),
        ("System Fields", {
            "fields": ("verification_token", "reissued"),
        }),
    )

    def save_model(self, request, obj, form, change):
        was_new = not change  # True if this is a new object

        super().save_model(request, obj, form, change)

    # Log creation if new
        if was_new:
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created certificate {obj.unique_id} - {obj.full_name}"
            )

    # Log reissue if reissue_date changed
        if change and 'reissue_date' in form.changed_data and obj.reissue_date:
            ReissueLog.objects.create(certificate=obj)
            obj.reissued = True
            obj.save(update_fields=['reissued'])


# ✅ Admin: Activity Logs
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "created_at")
    search_fields = ("user__username", "action")
    list_filter = ("created_at",)


# ✅ Admin: Digital Signatures
@admin.register(AdminSignature)
class AdminSignatureAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "bypass_digital_signature")
    search_fields = ("admin_user__username",)


# ✅ Admin: Certificate Templates
@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ("template_type", "uploaded_at")


# ✅ Admin: Reissue Logs
@admin.register(ReissueLog)
class ReissueLogAdmin(admin.ModelAdmin):
    list_display = ("certificate", "reissued_by", "reissued_at", "remarks")
    search_fields = ("certificate__unique_id", "reissued_by__username", "remarks")
    list_filter = ("reissued_at",)

