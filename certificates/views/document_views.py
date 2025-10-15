# certificates/views/document_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from pathlib import Path
from django.contrib import messages

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
import qrcode

from certificates.models import Certificate, AdminSignature, ActivityLog, CertificateTemplate
from certificates.decorators import role_required
from certificates.utils import TEMPLATE_MAP, _ensure_dirs


# ---------------- Certificate Generation ----------------
@login_required
def generate_certificate(request, pk, skip_log=False):
    cert = get_object_or_404(Certificate, pk=pk)
    _ensure_dirs()

    tpl_path = None

    # ✅ Try to find uploaded template first
    uploaded_template = CertificateTemplate.objects.filter(template_type=cert.document_type).first()
    if uploaded_template and uploaded_template.file:
        tpl_path = Path(uploaded_template.file.path)
    else:
        # Fallback to default TEMPLATE_MAP
        tpl_filename = TEMPLATE_MAP.get(cert.document_type)
        if tpl_filename:
            tpl_path = Path(settings.MEDIA_ROOT) / "certificate_templates" / tpl_filename

    if not tpl_path or not tpl_path.exists():
        messages.error(request, f"Template file missing for '{cert.document_type}'.")
        return redirect("certificates:certificate_detail", pk=cert.pk)

    # ---------------- Generate QR code ----------------
    verify_url = request.build_absolute_uri(f"/certificates/verify/{cert.verification_token}/")
    qr_path = Path(settings.MEDIA_ROOT) / "qrcodes" / f"qr_{cert.pk}.png"
    qr_path.parent.mkdir(parents=True, exist_ok=True)
    qrcode.make(verify_url).save(qr_path)

    try:
        # ---------------- Load template ----------------
        doc = DocxTemplate(str(tpl_path))

        # ---------------- Handle signature ----------------
        signature_image_path = None
        default_signature_path = Path(settings.MEDIA_ROOT) / "signatures" / "default_signature.png"

        try:
            admin_signature = AdminSignature.objects.get(admin_user=request.user)
            if not admin_signature.bypass_digital_signature:
                if admin_signature.signature_image and admin_signature.signature_image.name:
                    signature_image_path = Path(settings.MEDIA_ROOT) / admin_signature.signature_image.name
                elif default_signature_path.exists():
                    signature_image_path = default_signature_path
        except AdminSignature.DoesNotExist:
            if default_signature_path.exists():
                signature_image_path = default_signature_path

        signature_inline = None
        if signature_image_path and signature_image_path.exists():
            signature_inline = InlineImage(doc, str(signature_image_path), width=Mm(40), height=Mm(12))

        # ---------------- Template context ----------------
        context = {
            "cert": cert,
            "full_name": cert.full_name,
            "age": cert.age or "",
            "address": cert.address or "",
            "occupation": cert.occupation or "",
            "purpose": cert.purpose or "",
            "resident_since": cert.resident_since or "",
            "date_issued": cert.created_at.strftime("%B %d, %Y") if cert.created_at else "",
            "date_reissued": cert.reissue_date.strftime("%B %d, %Y") if cert.reissue_date else None,
            "barangay": "Longos",
            "city": "Malabon City",
            "captain": "Maria Lourdes Casareo",
            "postal": "1472",
            "signature": signature_inline,
            "captain_signature": signature_inline,
            "qr_code": InlineImage(doc, str(qr_path), width=Mm(30)),
        }

        # Render and save document
        doc.render(context)

        docx_out_dir = Path(settings.MEDIA_ROOT) / "generated" / "docx"
        docx_out_dir.mkdir(parents=True, exist_ok=True)
        docx_name = f"{cert.document_type}_{cert.full_name.replace(' ', '_')}.docx"
        docx_out = docx_out_dir / docx_name
        doc.save(str(docx_out))

        cert.generated_docx.name = f"generated/docx/{docx_name}"
        cert.status = "COMPLETED"
        cert.save(update_fields=["generated_docx", "status"])

    except Exception as e:
        messages.error(request, f"Certificate generation error: {str(e)}")
        return redirect("certificates:certificate_detail", pk=cert.pk)

    # ---------------- Log activity ----------------
    if not skip_log:
        try:
            ActivityLog.objects.create(user=request.user, action=f"Created certificate {cert.id} - {cert.full_name}")
        except Exception as e:
            print(f"[Activity Log Error] {e}")

    return redirect("certificates:certificate_detail", pk=cert.pk)


# ---------------- DOCX Download ----------------
@login_required
@role_required(allowed_roles=["staff", "admin"])
def certificate_docx(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk)
    if not certificate.generated_docx or not Path(certificate.generated_docx.path).exists():
        return HttpResponse("Generated DOCX not found.", status=404)

    with open(certificate.generated_docx.path, "rb") as f:
        response = HttpResponse(
            f.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        response["Content-Disposition"] = f'attachment; filename=certificate_{pk}.docx'
        return response


# ---------------- Certificate Verification ----------------
@login_required
def verify_certificate(request, token):
    cert = get_object_or_404(Certificate, verification_token=token)
    return HttpResponse(f"Certificate for {cert.full_name} is valid.")


# ---------------- QR Code ----------------
@login_required
def certificate_qr(request, token):
    cert = get_object_or_404(Certificate, verification_token=token)
    qr_path = Path(settings.MEDIA_ROOT) / "qrcodes" / f"qr_{cert.pk}.png"
    qr_path.parent.mkdir(parents=True, exist_ok=True)

    if not qr_path.exists():
        verify_url = request.build_absolute_uri(f"/certificates/verify/{cert.verification_token}/")
        qrcode.make(verify_url).save(qr_path)

    with open(qr_path, "rb") as f:
        return HttpResponse(f.read(), content_type="image/png")
