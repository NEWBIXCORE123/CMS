# brgy_cms/certificates/views/auth_views.py
import logging
from django.urls import reverse_lazy, reverse
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from certificates.models import AccessAttempt

logger = logging.getLogger(__name__)

class CustomLoginView(LoginView):
    template_name = "certificates/login.html"

    def get(self, request, *args, **kwargs):
        # If already logged in → redirect to dashboard
        if request.user.is_authenticated:
            logger.debug("User authenticated, redirecting to dashboard")
            return redirect('certificates:dashboard')

        # Remove ?next= if user is logged out
        if 'next' in request.GET:
            logger.debug("Removing leftover ?next= parameter")
            return redirect('certificates:login')

        logger.debug(f"GET request context: {self.get_context_data()}")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        username = self.request.POST.get('username')
        logger.debug(f"Successful login for {username}, resetting AccessAttempt")
        AccessAttempt.objects.filter(username=username).delete()  # Reset attempts on successful login
        return super().form_valid(form)

    def form_invalid(self, form):
        username = self.request.POST.get('username')
        max_attempts = 5
        lockout_duration = timedelta(minutes=1)
        logger.debug(f"Form invalid for username: {username}")

        try:
            attempt = AccessAttempt.objects.get(username=username)
            time_since_last_attempt = timezone.now() - attempt.timestamp

            if attempt.failures_since_start >= max_attempts:
                if time_since_last_attempt < lockout_duration:
                    remaining_seconds = (lockout_duration - time_since_last_attempt).total_seconds()
                    logger.debug(f"User {username} is locked out, {remaining_seconds:.0f} seconds remaining")
                    return custom_lockout_response(self.request, lockout_duration=remaining_seconds)
                else:
                    logger.debug(f"Lockout expired for {username}, resetting attempts")
                    attempt.failures_since_start = 0

            attempt.failures_since_start += 1
            attempt.timestamp = timezone.now()
            attempt.save()

        except AccessAttempt.DoesNotExist:
            attempt = AccessAttempt.objects.create(
                username=username,
                failures_since_start=1,
                timestamp=timezone.now()
            )

        attempts_left = max(0, max_attempts - attempt.failures_since_start)
        if attempt.failures_since_start >= max_attempts:
            return custom_lockout_response(self.request, lockout_duration=lockout_duration.total_seconds())

        messages.error(self.request, "Incorrect username or password.")
        if attempts_left > 0:
            messages.info(self.request, f"Attempts left: {attempts_left}")

        return super().form_invalid(form)



def custom_lockout_response(request, lockout_duration=60, credentials=None, *args, **kwargs):
    logger.debug(f"Rendering lockout response with duration: {lockout_duration}")
    return render(
        request,
        "certificates/login.html",
        {
            "lockout_seconds": int(lockout_duration),
            "lockout_message": "🚫 Account locked: too many login attempts.",
            "attempts_left": 0,
        },
        status=200,
    )


@csrf_exempt
def reset_attempts(request):
    if request.method == "POST":
        username = request.POST.get('username')
        if username:
            AccessAttempt.objects.filter(username=username).delete()
            return JsonResponse({"ok": True, "clear_local_storage": True})
        return JsonResponse({"ok": False}, status=400)


def logout_view(request):
    """
    Secure logout:
    - Fully flushes session data.
    - Prevents back navigation after logout.
    - Always redirects cleanly to the login page.
    """
    from django.urls import reverse

    logout(request)
    request.session.flush()

    messages.success(request, "You have successfully logged out.")

    # Always redirect cleanly to login (no next param)
    login_url = reverse('certificates:login')
    response = redirect(login_url)

    # Prevent page caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response



@never_cache
@login_required
def home(request):
    return redirect('certificates:dashboard')



@never_cache
def landing_page(request):
    """
    Landing page:
    Redirect authenticated users to dashboard.
    """
    if request.user.is_authenticated:
        return redirect('certificates:dashboard')
    response = render(request, 'certificates/landingpage.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
