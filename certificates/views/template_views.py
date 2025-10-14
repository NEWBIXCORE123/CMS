from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from certificates.forms import CertificateTemplateForm
from certificates.models import CertificateTemplate
from certificates.decorators import role_required

@login_required
@role_required(allowed_roles=["admin", "superadmin"])
def manage_certificate_template(request):
    """
    Manage certificate templates.
    """
    if request.method == 'POST':
        form = CertificateTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_template = form.save()
            # ✅ Add success message with the uploaded filename
            messages.success(request, f"'{uploaded_template.file.name.split('/')[-1]}' uploaded successfully!")
            return redirect('certificates:manage_certificate_template')
    else:
        form = CertificateTemplateForm()

    # ✅ Collect current templates for display
    current_templates = {t.template_type: t for t in CertificateTemplate.objects.all()}

    return render(
        request,
        'certificates/manage_templates.html',
        {'form': form, 'current_templates': current_templates}
    )
