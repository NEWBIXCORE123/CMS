from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from certificates.models import ActivityLog 
from certificates.forms import OCRUploadForm 
from certificates.ocr import extract_from_image

@login_required
def ocr_upload(request):
    return render(request, "certificates/ocr_upload.html")

@csrf_exempt
@login_required
def ocr_extract_api(request):
    if request.method != "POST" or "image" not in request.FILES:
        return JsonResponse({"ok": False, "error": "POST 'image' file required."}, status=400)

    # Validate the upload form
    form = OCRUploadForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": form.errors.as_json()}, status=400)

    try:
        # Read bytes but do not run heavy OCR/ML
        img_bytes = request.FILES["image"].read()
        is_authorized = request.user.username in ["admin1", "super1"]
        bypass = form.cleaned_data.get("bypass_barangay_check", False)

        # Call the lightweight/dummy extractor which returns a friendly message
        ocr_result = extract_from_image(
            img_bytes,
            bypass_barangay_check=bypass,
            is_authorized=is_authorized
        )

        # Log admin bypass (if user explicitly used bypass) for audit trail
        if bypass and is_authorized:
            try:
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"⚠️ Admin attempted to bypass barangay check (OCR disabled) for manual entry."
                )
            except Exception:
                pass

        # Since OCR/ML is disabled, return a helpful response prompting manual entry
        return JsonResponse({
            "ok": True,
            "detected_id": ocr_result.get("detected_id", "disabled"),
            "full_name": ocr_result.get("full_name", ""),
            "age": ocr_result.get("age", ""),
            "address": ocr_result.get("address", ""),
            "occupation": "",
            "purpose": "",
            "resident_since": "",
            "id_type": ocr_result.get("id_type", ""),
            "raw_lines": ocr_result.get("raw_lines", []),
            "warning": ocr_result.get("warning", "OCR and ML are disabled on this deployment."),
            "predicted_document": {"type": "disabled", "confidence": 0.0},
            "bypass_used": bypass
        })

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
