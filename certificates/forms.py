from django import forms
from django.utils import timezone
from .models import Certificate, AdminSignature, CertificateTemplate
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


class CertificateForm(forms.ModelForm):
    # Add bypass_barangay_check field
    bypass_barangay_check = forms.BooleanField(
        required=False,
        label="Bypass Barangay Address Check",
        help_text="Check to allow addresses outside of Longos (admin only)."
    )

    class Meta:
        model = Certificate
        fields = [
            "full_name",
            "address",
            "age",
            "occupation",
            "purpose",
            "resident_since",
            "document_type",
            "bypass_barangay_check",  # Include the new field
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "document_type": forms.Select(attrs={"placeholder": "-- choose --"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # Capture user from kwargs
        super().__init__(*args, **kwargs)
        self.fields["resident_since"].required = False
        # Restrict bypass_barangay_check to authorized admins
        if not self.user or self.user.username not in ["admin1", "super1"]:
            self.fields.pop("bypass_barangay_check", None)

    def clean_address(self):
        address = self.cleaned_data.get("address", "").lower()
        allowed_barangay = getattr(settings, "ALLOWED_BARANGAY", "longos").lower()
        bypass = self.cleaned_data.get("bypass_barangay_check", False)

        # Skip barangay check if bypass is enabled and user is authorized
        if not bypass or (self.user and self.user.username not in ["admin1", "super1"]):
            if allowed_barangay not in address:
                raise forms.ValidationError(
                    f"Address must contain Barangay {allowed_barangay.title()}."
                )
        return address

    def clean(self):
        cleaned_data = super().clean()
        full_name = cleaned_data.get("full_name")
        doc_type = cleaned_data.get("document_type")
        purpose = cleaned_data.get("purpose")

        if full_name and doc_type and purpose:
            existing = Certificate.objects.filter(
                full_name__iexact=full_name.strip(),
                document_type=doc_type,
                purpose__iexact=purpose.strip(),
            ).exclude(pk=self.instance.pk)

            conflict = next(
                (
                    cert for cert in existing
                    if not cert.is_expired() and cert.status in ["PENDING", "COMPLETED"]
                ),
                None
            )

            if conflict:
                self.add_error(
                    None,
                    f"A {conflict.get_document_type_display()} certificate for '{full_name}' "
                    f"with purpose '{purpose}' already exists and is still active until "
                    f"{conflict.expiration_date.strftime('%B %d, %Y')}."
                )
                raise forms.ValidationError("Duplicate certificate detected.")

        return cleaned_data


class OCRUploadForm(forms.Form):
    image = forms.ImageField(
        required=True,
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"})
    )
    bypass_barangay_check = forms.BooleanField(
        required=False,
        label="Bypass Barangay Address Check",
        help_text="Only available for authorized admins"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Only allow specific admins to see the checkbox
        if not user or user.username not in ["admin1", "super1"]:
            self.fields.pop("bypass_barangay_check", None)

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("image")
        bypass = cleaned_data.get("bypass_barangay_check", False)
        # Add any image-specific validation if needed
        if image and not image.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            raise forms.ValidationError("Only PNG, JPG, or JPEG files are allowed.")
        return cleaned_data




class DigitalSignatureForm(forms.ModelForm):
    class Meta:
        model = AdminSignature
        fields = ["signature_image", "bypass_digital_signature"]
        widgets = {
            "signature_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/png"}),
            "bypass_digital_signature": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        # Accept 'user' keyword argument from the view
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_signature_image(self):
        signature_image = self.cleaned_data.get("signature_image")
        bypass_digital_signature = self.cleaned_data.get("bypass_digital_signature", False)
        instance_exists = self.instance is not None
        existing_image = instance_exists and self.instance.signature_image

        # If bypassing, no image is required
        if bypass_digital_signature:
            return signature_image

        # Require an image if not bypassing and no existing image
        if not signature_image and not existing_image:
            raise forms.ValidationError("A signature image is required unless bypassing digital signature.")

        # Validate new uploads
        if isinstance(signature_image, UploadedFile):
            if signature_image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Signature image must not exceed 2MB.")
            if signature_image.content_type != "image/png":
                raise forms.ValidationError("Signature image must be in PNG format.")
        elif signature_image is None and existing_image:
            return self.instance.signature_image
        elif signature_image and not signature_image.name.lower().endswith('.png'):
            raise forms.ValidationError("Signature image must be in PNG format.")

        return signature_image



class CertificateTemplateForm(forms.ModelForm):
    class Meta:
        model = CertificateTemplate
        fields = ['template_type', 'file']
        widgets = {
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'template_type': 'Certificate Type',
            'file': 'Template File (.docx)',
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.lower().endswith('.docx'):
                raise forms.ValidationError("Only .docx files are allowed.")
            if file.size > 5 * 1024 * 1024:  # 5MB max
                raise forms.ValidationError("File size must not exceed 5MB.")
        return file

    def clean(self):
        cleaned_data = super().clean()
        template_type = cleaned_data.get('template_type')
        if template_type:
            existing = CertificateTemplate.objects.filter(template_type=template_type).first()
            # If a template exists, allow it — it will be replaced in the view
            if existing and not self.instance.pk:
                self.instance = existing
        return cleaned_data