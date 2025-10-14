# certificates/views/report_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.cache import never_cache

from docxtpl import DocxTemplate
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import json

from certificates.models import Certificate, ReissueLog
from certificates.decorators import role_required

# ---------------- Reports Dashboard ----------------
@never_cache
@login_required
@role_required(allowed_roles=["staff", "admin"])
def reports(request):
    # --- Generated Certificates (Completed) ---
    generated_certs = Certificate.objects.filter(status__iexact="completed").count()

    # --- Reissued Certificates ---
    reissued_logs = ReissueLog.objects.select_related('certificate')
    reissued_certs = reissued_logs.count()

    # --- Pending Certificates ---
    pending_certs = Certificate.objects.filter(status__iexact="pending").count()

    # --- Total Certificates ---
    total_certs = generated_certs + reissued_certs

    # --- Certificates by Document Type (Completed + Reissued) ---
    completed_or_reissued = Certificate.objects.filter(
        Q(status__iexact="completed") | Q(reissued=True)
    )
    cert_counts = completed_or_reissued.values("document_type").annotate(total=Count("id")).order_by("document_type")
    reissue_type_counts = reissued_logs.values("certificate__document_type").annotate(total=Count("id"))

    # Merge reissue counts into cert_counts
    reissue_map = {r["certificate__document_type"]: r["total"] for r in reissue_type_counts}
    merged_counts_list = [{"document_type": c["document_type"], "total": c["total"] + reissue_map.get(c["document_type"], 0)} for c in cert_counts]

    # --- Purpose Breakdown ---
    purpose_counts = completed_or_reissued.values("purpose").annotate(total=Count("id"))
    purpose_counts_list = list(purpose_counts)

    # --- Monthly Trends ---
    monthly_counts_qs = completed_or_reissued.values("created_at").annotate(
        new_total=Count("id", filter=Q(status__iexact="completed")),
        reissued_total=Count("id", filter=Q(reissued=True))
    ).order_by("created_at")

    monthly_counts = []
    years = set()
    for item in monthly_counts_qs:
        month_str = item["created_at"].strftime("%Y-%m-01")
        year = item["created_at"].year
        years.add(year)
        monthly_counts.append({
            "month": month_str,
            "new_total": item["new_total"],
            "reissued_total": item["reissued_total"]
        })
    years = sorted(list(years))

    # --- New vs Reissued total ---
    new_vs_reissue = {"new": generated_certs, "reissued": reissued_certs}

    return render(request, "certificates/reports.html", {
        "cert_counts": merged_counts_list,
        "purpose_counts": purpose_counts_list,
        "monthly_counts": monthly_counts,
        "years": years,
        "new_vs_reissue": new_vs_reissue,
        "total_certs": total_certs,
        "generated_certs": generated_certs,
        "reissued_certs": reissued_certs,
        "pending_certs": pending_certs,
    })


# ---------------- PDF Export ----------------
@login_required
def reports_pdf(request):
    # --- Accurate Dashboard-Matching Counts ---
    generated_certs = Certificate.objects.filter(status__iexact="completed").count()
    reissued_certs = ReissueLog.objects.count()
    pending_certs = Certificate.objects.filter(status__iexact="pending").count()
    total_certs = generated_certs + reissued_certs

    # --- Aggregations ---
    cert_counts = Certificate.objects.filter(
        Q(status__iexact="completed") | Q(reissued=True)
    ).values("document_type").annotate(total=Count("id")).order_by("document_type")

    purpose_counts = Certificate.objects.filter(
        Q(status__iexact="completed") | Q(reissued=True)
    ).values("purpose").annotate(total=Count("id")).order_by("purpose")

    # --- HTTP Response Setup ---
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="Barangay_Reports.pdf"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"

    # --- PDF Document ---
    pdf = SimpleDocTemplate(response, pagesize=A4, topMargin=30, bottomMargin=30)
    pdf.title = "Barangay Reports Summary"

    story = []
    styles = getSampleStyleSheet()

    # --- Styles ---
    title_style = ParagraphStyle(name="Title", fontSize=18, leading=22, alignment=1, spaceAfter=20, fontName="Helvetica-Bold")
    section_style = ParagraphStyle(name="Section", fontSize=14, leading=18, spaceBefore=12, spaceAfter=8, fontName="Helvetica-Bold", textColor=colors.HexColor("#333"))
    normal_style = styles["Normal"]

    # --- Logo ---
    logo_path = os.path.join(settings.BASE_DIR, "certificates", "static", "images", "logo.png")
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=60, height=60))
        story.append(Spacer(1, 6))

    # --- Header ---
    story.append(Paragraph("BARANGAY LONGOS – REPORTS SUMMARY", title_style))
    story.append(Paragraph(f"Date Generated: {timezone.now().strftime('%B %d, %Y')}", normal_style))
    story.append(Spacer(1, 12))

    # --- Summary Section ---
    story.append(Paragraph("SUMMARY", section_style))
    story.append(Paragraph(f"Total Certificates (Generated + Reissued): <b>{total_certs}</b>", normal_style))
    story.append(Paragraph(f"Generated Certificates (Completed): <b>{generated_certs}</b>", normal_style))
    story.append(Paragraph(f"Reissued Certificates: <b>{reissued_certs}</b>", normal_style))
    story.append(Paragraph(f"Pending Certificates: <b>{pending_certs}</b>", normal_style))
    story.append(Spacer(1, 12))

    # --- Certificates by Type ---
    story.append(Paragraph("CERTIFICATES BY TYPE", section_style))
    data = [["Document Type", "Total"]] + [[c["document_type"], c["total"]] for c in cert_counts]
    table = Table(data, colWidths=[250, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f81bd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 18))

    # --- Purpose Breakdown ---
    story.append(Paragraph("PURPOSE BREAKDOWN", section_style))
    purpose_data = [["Purpose", "Total"]] + [[p["purpose"] or "Unknown", p["total"]] for p in purpose_counts]
    purpose_table = Table(purpose_data, colWidths=[250, 100])
    purpose_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#70ad47")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(purpose_table)
    story.append(Spacer(1, 24))

    # --- Footer ---
    story.append(Paragraph("<i>Generated automatically by the Barangay Certificate Management System</i>", normal_style))

    pdf.build(story)
    return response
