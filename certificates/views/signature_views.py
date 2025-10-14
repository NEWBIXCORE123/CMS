from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from certificates.forms import DigitalSignatureForm
from certificates.decorators import role_required
from certificates.models import AdminSignature

@login_required
@role_required(allowed_roles=["admin"])
def digital_signature_upload(request):
    """
    Handle the upload of an admin's digital signature.
    """
    try:
        signature_instance = AdminSignature.objects.get(admin_user=request.user)
    except AdminSignature.DoesNotExist:
        signature_instance = None

    if request.method == "POST":
        form = DigitalSignatureForm(request.POST, request.FILES, user=request.user, instance=signature_instance)
        if form.is_valid():
            sig = form.save(commit=False)
            sig.admin_user = request.user  # Ensure the signature is linked to the logged-in admin
            sig.save()
            bypass_status = "Enabled" if sig.bypass_digital_signature else "Disabled"
            messages.success(request, f"Digital signature settings updated. Bypass: {bypass_status}.")
            return redirect('certificates:digital_signature_upload')
        else:
            messages.error(request, "⚠️ Please fix the errors below.")
    else:
        form = DigitalSignatureForm(user=request.user, instance=signature_instance)

    return render(request, "certificates/upload_signature.html", {"form": form})
