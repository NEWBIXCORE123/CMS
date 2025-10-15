from django.urls import path
from certificates.views import (
    CustomLoginView,
    logout_view,
    reset_attempts,
    home,
    landing_page,
    dashboard,
    mobile_capture,
    latest_mobile_image,
    mobile_upload,
    ocr_upload,
    ocr_extract_api,
    digital_signature_upload,
    activity_logs,
    report_views,
    reports_pdf,
    manage_certificate_template,
    check_age,
)

# Split views
from certificates.views import certificate_views
from certificates.views import document_views  # contains generate_certificate, certificate_docx, verify_certificate, certificate_qr

app_name = "certificates"

urlpatterns = [
    # ---------------- AUTH ----------------
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("reset-attempts/", reset_attempts, name="reset_attempts"),

    # ---------------- DASHBOARD & HOME ----------------
    path("", certificate_views.list_certificates, name="list_certificates"),  # /certificates/
    path("dashboard/", dashboard, name="dashboard"),
    path("home/", home, name="home"),
    path("landingpage/", landing_page, name="landingpage"),

    # ---------------- MOBILE CAPTURE / UPLOAD ----------------
    path("mobile-capture/", mobile_capture, name="mobile_capture"),
    path("mobile-upload/", mobile_upload, name="mobile_upload"),
    path("latest-mobile-image/", latest_mobile_image, name="latest_mobile_image"),

    # ---------------- OCR & ML ----------------
    path("ocr-upload/", ocr_upload, name="ocr_upload"),
    path("ocr-extract/", ocr_extract_api, name="ocr_extract_api"),

    # ---------------- CERTIFICATE MANAGEMENT ----------------
    path("create/", certificate_views.create_certificate, name="create_certificate"),
    path("<int:pk>/", certificate_views.certificate_detail, name="certificate_detail"),
    path("<int:pk>/generate/", document_views.generate_certificate, name="generate_certificate"),
    path("<int:pk>/docx/", document_views.certificate_docx, name="certificate_docx"),
    path("reissue/<int:pk>/", certificate_views.reissue_certificate, name="reissue_certificate"),

    # ---------------- SIGNATURES & LOGS ----------------
    path("upload-signature/", digital_signature_upload, name="digital_signature_upload"),
    path("activity-logs/", activity_logs, name="activity_logs"),

    # ---------------- CERTIFICATE VERIFICATION ----------------
    path("verify/<uuid:token>/", document_views.verify_certificate, name="verify_certificate"),
    path("qr/<uuid:token>/", document_views.certificate_qr, name="certificate_qr"),
    path("check-age/", check_age, name="check_age"),

    # ---------------- REPORTS & TEMPLATES ----------------
    path("reports/", report_views.reports, name="reports"),
    path("reports/pdf/", reports_pdf, name="reports_pdf"),
    path("manage-templates/", manage_certificate_template, name="manage_certificate_template"),
]
