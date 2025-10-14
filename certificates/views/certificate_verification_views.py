# certificates/views/certificate_verification_views.py
from django.shortcuts import render, get_object_or_404
from certificates.models import Certificate
from django.http import HttpResponse
import qrcode
from io import BytesIO
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def verify_certificate(request, token):
    """
    Verify a certificate using its UUID token.
    """
    certificate = get_object_or_404(Certificate, verification_token=token)
    context = {
        'cert': certificate,
        'valid': not certificate.is_expired() and certificate.status == 'COMPLETED',
        'expired': certificate.is_expired(),
    }
    return render(request, 'certificates/verify_certificate.html', context)

def certificate_qr(request, token):
    """
    Generate QR code for certificate verification.
    """
    # Get the certificate object
    certificate = get_object_or_404(Certificate, verification_token=token)

    # Build the absolute verification URL using Django's reverse
    verification_url = request.build_absolute_uri(
        reverse("certificates:verify_certificate", args=[certificate.verification_token])
    )

    # Generate the QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(verification_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Prepare the response as PNG
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    response = HttpResponse(content_type="image/png")
    response.write(buffer.getvalue())
    return response


@csrf_exempt
def check_age(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        age = int(data.get('age', 0))
        return JsonResponse({'isMinor': age < 18})
    return JsonResponse({'error': 'Invalid request'}, status=400)