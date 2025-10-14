from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Count
from certificates.models import Certificate, ReissueLog
from certificates.decorators import role_required

@never_cache
@login_required
@role_required(allowed_roles=["staff", "admin"])
def dashboard(request):
    # --- Generated Certificates ---
    generated_certs_qs = Certificate.objects.filter(status__iexact="completed")
    generated_certs = generated_certs_qs.count()

    # --- Reissued Certificates ---
    reissued_logs_qs = ReissueLog.objects.select_related("certificate")
    reissued_certs = reissued_logs_qs.count()

    # --- Total Certificates (Generated + Reissued) ---
    total_certs = generated_certs + reissued_certs

    # --- Certificates by Document Type (Generated + Reissued) ---
    cert_counts = (
        Certificate.objects.filter(Q(status__iexact="completed") | Q(reissued=True))
        .values("document_type")
        .annotate(total=Count("id"))
        .order_by("document_type")
    )

    # --- Add ReissueLog counts per document type ---
    reissue_type_counts = (
        ReissueLog.objects.values("certificate__document_type")
        .annotate(total=Count("id"))
    )

    # Merge reissue counts into cert_counts
    reissue_map = {r["certificate__document_type"]: r["total"] for r in reissue_type_counts}
    merged_counts = []
    for c in cert_counts:
        doc_type = c["document_type"]
        total = c["total"] + reissue_map.get(doc_type, 0)
        merged_counts.append({"document_type": doc_type, "total": total})

    # --- Recent Certificates (latest created or reissued) ---
    certs = Certificate.objects.all().order_by("-created_at")
    paginator = Paginator(certs, 5)
    page_number = request.GET.get("page")
    recent_certs = paginator.get_page(page_number)

    #  Pass reissued and generated counts to template
    return render(request, "certificates/dashboard.html", {
        "recent_certs": recent_certs,
        "cert_counts": merged_counts,
        "total_certs": total_certs,
        "generated_certs": generated_certs,
        "reissued_certs": reissued_certs,
    })
