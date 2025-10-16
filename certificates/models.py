import uuid
import os
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .utils import generate_unique_id
from django.conf import settings

import uuid
import os
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .utils import generate_unique_id

# -------------------------------------------------
# USER ROLE PROFILE (RBAC)
# -------------------------------------------------
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('superadmin', 'SuperAdmin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_staff_role(self):
        return self.role == 'staff'

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    @property
    def is_superadmin_role(self):
        return self.role == 'superadmin' or self.user.is_superuser


# -------------------------------------------------
# CHOICES
# -------------------------------------------------
DOCUMENT_CHOICES = [
    ("clearance", "Clearance"),
    ("residency", "Residency"),
    ("indigency", "Indigency"),
]

STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("COMPLETED", "Completed"),
]


# -------------------------------------------------
# CERTIFICATE MODEL
# -------------------------------------------------
class Certificate(models.Model):
    unique_id = models.CharField(max_length=20, unique=True, editable=False, blank=True, null=True)

    full_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    occupation = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    resident_since = models.CharField(max_length=50, blank=True, null=True)

    document_type = models.CharField(max_length=50, choices=DOCUMENT_CHOICES, default="residency")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="PENDING")

    generated_docx = models.FileField(upload_to="generated/docx/", blank=True, null=True)
    generated_pdf = models.FileField(upload_to="generated/pdf/", blank=True, null=True)

    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    expiration_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ NEW FIELD (for reissued certificates)
    reissue_date = models.DateTimeField(blank=True, null=True)
    reissued = models.BooleanField(default=False)

    def is_expired(self):
        return self.expiration_date and timezone.now() > self.expiration_date

    def clean(self):
        """
        Prevent duplicate active certificates for the same name, document type, and purpose.
        """
        if self.full_name and self.document_type and self.purpose:
            existing = Certificate.objects.filter(
                full_name__iexact=self.full_name.strip(),
                document_type=self.document_type,
                purpose__iexact=self.purpose.strip(),
            ).exclude(pk=self.pk)

            for cert in existing:
                if not cert.is_expired() and cert.status in ["PENDING", "COMPLETED"]:
                    raise ValidationError(
                        f"A {self.get_document_type_display()} certificate for '{self.full_name}' "
                        f"with purpose '{self.purpose}' already exists and is still active."
                    )

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = generate_unique_id(self.document_type)
        if not self.expiration_date:
            issue_date = self.reissue_date or self.created_at or timezone.now()
            try:
                # Set expiration to one year from issue_date (same day and month, next year)
                self.expiration_date = issue_date.replace(year=issue_date.year + 1)
            except ValueError:
                # Handle leap year edge case (e.g., February 29)
                # If next year is not a leap year, set to February 28
                if issue_date.month == 2 and issue_date.day == 29:
                    self.expiration_date = issue_date.replace(year=issue_date.year + 1, day=28)
                else:
                    raise

        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)

    def reissue(self):
        """
        Mark this certificate as reissued.
        Updates reissue_date, resets generated files, and updates expiration_date.
        """
        self.reissue_date = timezone.now()
        self.generated_docx = None
        self.generated_pdf = None
        self.reissued = True
        # Update expiration_date to one year from reissue_date
        try:
            self.expiration_date = self.reissue_date.replace(year=self.reissue_date.year + 1)
        except ValueError:
            # Handle leap year edge case
            if self.reissue_date.month == 2 and self.reissue_date.day == 29:
                self.expiration_date = self.reissue_date.replace(year=self.reissue_date.year + 1, day=28)
            else:
                raise
        self.save()

    @property
    def date_issued(self):
        """Return reissue_date if exists, otherwise original created_at"""
        return self.reissue_date or self.created_at

    def __str__(self):
        return f"{self.unique_id} - {self.full_name or 'Unnamed Certificate'}"


class ReissueLog(models.Model):
    certificate = models.ForeignKey('Certificate', on_delete=models.CASCADE, related_name='reissue_logs')
    reissued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reissued_at = models.DateTimeField(auto_now_add=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Reissue of {self.certificate.unique_id} by {self.reissued_by or 'System'} on {self.reissued_at.strftime('%Y-%m-%d %H:%M')}"


# -------------------------------------------------
# ACTIVITY LOG
# -------------------------------------------------
class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed', 'Failed'),
        ('create', 'Create'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='other')
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def simple_type(self):
        return self.action_type.capitalize()

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.action}"
        return f"{self.action}"



# -------------------------------------------------
# ADMIN SIGNATURE
# -------------------------------------------------
class AdminSignature(models.Model):
    admin_user = models.OneToOneField(User, on_delete=models.CASCADE)
    signature_image = models.ImageField(upload_to="signatures/", null=True, blank=True)
    bypass_digital_signature = models.BooleanField(default=False, help_text="If true, certificates will leave space for manual signing.")

    def __str__(self):
        return f"Signature for {self.admin_user.username}"


# -------------------------------------------------
# CERTIFICATE TEMPLATE
# -------------------------------------------------
class CertificateTemplate(models.Model):
    template_type = models.CharField(max_length=50, choices=DOCUMENT_CHOICES, unique=True)

    def template_upload_path(instance, filename):
        # Always save using the template type as filename
        filename = f"{instance.template_type}.docx"
        upload_dir = "certificate_templates"
        full_path = os.path.join(upload_dir, filename)

        # Compute absolute file path
        full_abs_path = os.path.join(settings.MEDIA_ROOT, full_path)

        # If a file with the same name exists, remove it first
        if os.path.exists(full_abs_path):
            os.remove(full_abs_path)

        return full_path

    file = models.FileField(upload_to=template_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_template_type_display()} Template"



# -------------------------------------------------
# ACCESS ATTEMPT (for login failure tracking)
# -------------------------------------------------
class AccessAttempt(models.Model):
    username = models.CharField(max_length=255)
    failures_since_start = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} - {self.failures_since_start} failures"