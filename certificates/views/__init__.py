# certificates/views/__init__.py
from .auth_views import CustomLoginView, custom_lockout_response, reset_attempts, logout_view, home, landing_page
from .dashboard_views import dashboard
from .mobile_capture_views import mobile_capture, latest_mobile_image, mobile_upload
from .ocr_views import ocr_upload, ocr_extract_api
from .certificate_views import create_certificate, list_certificates, certificate_detail, reissue_certificate
from .document_views import generate_certificate, certificate_docx
from .signature_views import digital_signature_upload
from .log_views import activity_logs
from .certificate_verification_views import verify_certificate, certificate_qr, check_age
from .report_views import reports, reports_pdf  # Ensure this line is correct
from .template_views import manage_certificate_template