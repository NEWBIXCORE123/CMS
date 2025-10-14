from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from .models import ActivityLog

# ---------------- LOGIN ----------------
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Logs successful user login"""
    if user and user.is_authenticated:
        ActivityLog.objects.create(
            user=user,
            action=f"{user.username} logged in"
        )

# ---------------- LOGOUT ----------------
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Logs user logout"""
    if user and user.is_authenticated:
        ActivityLog.objects.create(
            user=user,
            action=f"{user.username} logged out"
        )

# ---------------- FAILED LOGIN ----------------
@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """
    Logs failed login attempts (prevents duplicates within 5 seconds)
    """
    username = credentials.get('username', None)
    if not username:
        return

    # Avoid duplicate logs within 5 seconds
    last_log = ActivityLog.objects.filter(
        action__icontains=f"Failed login attempt for username: {username}"
    ).order_by('-created_at').first()

    if last_log and (timezone.now() - last_log.created_at).total_seconds() < 5:
        return

    # Try to associate the User if it exists
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    ActivityLog.objects.create(
        user=user,
        action=f"Failed login attempt for username: {username}"
    )
