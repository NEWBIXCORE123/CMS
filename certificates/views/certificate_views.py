from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from certificates.models import Certificate, ReissueLog, ActivityLog
from certificates.forms import CertificateForm
from certificates.decorators import role_required
from .document_views import generate_certificate  # DOCX generation helper

# ---------------- CREATE CERTIFICATE ----------------
@login_required
@csrf_exempt
@role_required(allowed_roles=["staff", "admin"])
def create_certificate(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Invalid request"})

    form = CertificateForm(request.POST, user=request.user)
    if not form.is_valid():
        non_field_errors = form.non_field_errors()
        field_errors = [err for errs in form.errors.values() for err in errs]
        error_message = non_field_errors[0] if non_field_errors else (field_errors[0] if field_errors else "Something went wrong.")
        return JsonResponse({"ok": False, "error": error_message})

    try:
        certificate = form.save()
        ActivityLog.objects.create(
            user=request.user,
            action=f"Created certificate for {certificate.full_name} ({certificate.document_type})"
        )
        return JsonResponse({"ok": True, "id": certificate.id})
    except ValueError as e:
        return JsonResponse({"ok": False, "error": f"Date error: {str(e)}"})


# ---------------- LIST CERTIFICATES ----------------
@login_required
def list_certificates(request):
    search = request.GET.get('search', '')
    document_type = request.GET.get('document_type', '')
    status = request.GET.get('status', '')
    certificates = Certificate.objects.all()

    if search:
        certificates = certificates.filter(Q(full_name__icontains=search) | Q(address__icontains=search))
    if document_type:
        certificates = certificates.filter(document_type__iexact=document_type)
    if status:
        certificates = certificates.filter(status__iexact=status)

    paginator = Paginator(certificates.order_by('-created_at'), 9)
    page_number = request.GET.get('page')
    certificates = paginator.get_page(page_number)
    return render(request, 'certificates/list_certificates.html', {'certificates': certificates})


# ---------------- CERTIFICATE DETAIL ----------------
@login_required
def certificate_detail(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    return render(request, "certificates/certificate_detail.html", {"cert": cert})


# ---------------- REISSUE CERTIFICATE ----------------
@login_required
@role_required(allowed_roles=["staff", "admin"])
def reissue_certificate(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    try:
        cert.reissue()
        ReissueLog.objects.create(
            certificate=cert,
            reissued_by=request.user,
            remarks=f"Reissued {cert.get_document_type_display()} certificate for {cert.full_name}"
        )
        generate_certificate(request, pk=cert.pk, skip_log=True)
        ActivityLog.objects.create(
            user=request.user,
            action=f"Reissued {cert.get_document_type_display()} certificate for {cert.full_name}"
        )
        messages.success(request, f"✅ Certificate for {cert.full_name} has been successfully reissued and regenerated.")
    except Exception as e:
        messages.error(request, f"⚠️ Reissue failed: {str(e)}")
    return redirect("certificates:certificate_detail", pk=cert.pk)
