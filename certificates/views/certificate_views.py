# certificates/views/certificate_views.py
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


# ---------------- CERTIFICATE CRUD ----------------

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

        if non_field_errors:
            error_message = f"Duplicate Request Detected:\n\n{non_field_errors[0]}"
        elif field_errors:
            error_message = field_errors[0]
        else:
            error_message = "Something went wrong. Please try again."

        return JsonResponse({"ok": False, "error": error_message})

    try:
        certificate = form.save()

        # Activity log
        try:
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created certificate for {certificate.full_name} ({certificate.document_type})"
            )
        except Exception as e:
            print(f"[Activity Log Error] {e}")

        return JsonResponse({"ok": True, "id": certificate.id})

    except ValueError as e:
        return JsonResponse({"ok": False, "error": f"Date error: {str(e)}"})


@login_required
def list_certificates(request):
    search = request.GET.get('search', '')
    document_type = request.GET.get('document_type', '')
    status = request.GET.get('status', '')

    certificates = Certificate.objects.all()

    if search:
        certificates = certificates.filter(
            Q(full_name__icontains=search) |
            Q(address__icontains=search)
        )

    if document_type:
        certificates = certificates.filter(document_type__iexact=document_type)

    if status:
        certificates = certificates.filter(status__iexact=status)

    paginator = Paginator(certificates.order_by('-created_at'), 9)
    page_number = request.GET.get('page')
    certificates = paginator.get_page(page_number)

    return render(request, 'certificates/list_certificates.html', {'certificates': certificates})


@login_required
def certificate_detail(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    return render(request, "certificates/certificate_detail.html", {"cert": cert})


@login_required
@role_required(allowed_roles=["staff", "admin"])
def reissue_certificate(request, pk):
    cert = get_object_or_404(Certificate, id=pk)

    try:
        # Update certificate reissue
        cert.reissue()

        # Log reissue
        ReissueLog.objects.create(
            certificate=cert,
            reissued_by=request.user,
            remarks=f"Reissued {cert.get_document_type_display()} certificate for {cert.full_name}"
        )

        # Regenerate certificate DOCX
        generate_certificate(request, pk=cert.pk, skip_log=True)

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Reissued {cert.get_document_type_display()} certificate for {cert.full_name}"
        )

        messages.success(
            request,
            f"✅ Certificate for {cert.full_name} has been successfully reissued and regenerated."
        )

        return redirect("certificates:certificate_detail", pk=cert.pk)

    except ValueError as e:
        messages.error(request, f"⚠️ Reissue failed: Date error: {str(e)}")
        return redirect("certificates:certificate_detail", pk=cert.pk)
    except Exception as e:
        messages.error(request, f"⚠️ Reissue failed: {str(e)}")
        return redirect("certificates:certificate_detail", pk=cert.pk)
