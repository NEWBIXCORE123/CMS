import os
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.conf import settings

@login_required
def mobile_capture(request):
    captures_dir = os.path.join(settings.MEDIA_ROOT, "captures")
    latest_file_url = None
    if os.path.exists(captures_dir):
        files = sorted(os.listdir(captures_dir), reverse=True)
        if files:
            latest_file_url = f"{settings.MEDIA_URL}captures/{files[0]}"
    return render(request, "certificates/mobile_capture.html", {
        "latest_file_url": latest_file_url,
        "timestamp": datetime.now().timestamp(),
    })

@login_required
def latest_mobile_image(request):
    captures_dir = os.path.join(settings.MEDIA_ROOT, "captures")
    if not os.path.exists(captures_dir):
        return JsonResponse({"ok": False, "error": "No captures folder."})

    files = [f for f in os.listdir(captures_dir) if os.path.isfile(os.path.join(captures_dir, f))]
    if not files:
        return JsonResponse({"ok": False, "error": "No images found."})

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(captures_dir, f)))
    url = f"{settings.MEDIA_URL}captures/{latest_file}"
    return JsonResponse({"ok": True, "url": url})

@csrf_exempt
@login_required
def mobile_upload(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST request required."}, status=400)
    if "image" not in request.FILES:
        return JsonResponse({"ok": False, "error": "No image uploaded."}, status=400)

    try:
        image = request.FILES["image"]
        save_dir = os.path.join(settings.MEDIA_ROOT, "captures")
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.name}"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, "wb+") as f:
            for chunk in image.chunks():
                f.write(chunk)

        file_url = f"{settings.MEDIA_URL}captures/{filename}"
        return JsonResponse({"ok": True, "url": file_url})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
