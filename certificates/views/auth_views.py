# brgy_cms/certificates/views/auth_views.py
import logging
from datetime import timedelta
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from certificates.models import AccessAttempt

logger = logging.getLogger(__name__)

class CustomLoginView(LoginView):
    template_name = "certificates/login.html"

    # Always ensure context has lockout info
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('lockout_seconds', 0)
        context.setdefault('attempts_left', None)
        context.setdefault('lockout_message', '')
        return context

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('certificates:dashboard')
        if 'next' in request.GET:
            return redirect('certificates:login')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        username = self.request.POST.get('username', '').strip()
        AccessAttempt.objects.filter(username=username).delete()  # reset attempts
        return super().form_valid(form)

    def form_invalid(self, form):
        try:
            username = self.request.POST.get('username', '').strip()
            max_attempts = 5
            lockout_duration = timedelta(minutes=1)

            attempt, created = AccessAttempt.objects.get_or_create(
                username=username,
                defaults={'failures_since_start': 0, 'timestamp': timezone.now()}
            )

            if attempt.failures_since_start >= max_attempts:
                elapsed = timezone.now() - attempt.timestamp
                if elapsed < lockout_duration:
                    remaining_seconds = int((lockout_duration - elapsed).total_seconds())
                    return custom_lockout_response(self.request, lockout_duration=remaining_seconds)
                else:
                    attempt.failures_since_start = 0

            attempt.failures_since_start += 1
            attempt.timestamp = timezone.now()
            attempt.save()

            attempts_left = max(0, max_attempts - attempt.failures_since_start)
            if attempt.failures_since_start >= max_attempts:
                return custom_lockout_response(self.request, lockout_duration=int(lockout_duration.total_seconds()))

            messages.error(self.request, "Incorrect username or password.")
            if attempts_left > 0:
                messages.info(self.request, f"Attempts left: {attempts_left}")

        except Exception as e:
            logger.error(f"Error during login attempt: {e}", exc_info=True)
            messages.error(self.request, "An unexpected error occurred. Please try again later.")

        return super().form_invalid(form)


def custom_lockout_response(request, lockout_duration=60):
    return render(
        request,
        "certificates/login.html",
        {
            "lockout_seconds": int(lockout_duration),
            "attempts_left": 0,
            "lockout_message": "🚫 Account locked: too many login attempts.",
        },
        status=200,
    )


@csrf_exempt
def reset_attempts(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        if username:
            AccessAttempt.objects.filter(username=username).delete()
            return JsonResponse({"ok": True, "clear_local_storage": True})
        return JsonResponse({"ok": False}, status=400)


def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have successfully logged out.")
    response = redirect('certificates:login')
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
    if request.user.is_authenticated:
        return redirect('certificates:dashboard')
    response = render(request, 'certificates/landingpage.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
