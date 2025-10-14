# brgy_cms/certificates/decorators.py
from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles=[]):
    """
    Restrict access based on user role.
    Superusers always have full access.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in first.")
                return redirect('certificates:login')  # Namespaced URL

            if hasattr(request.user, 'profile'):
                role = request.user.profile.role
            else:
                role = 'staff'

            if request.user.is_superuser or role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "You don't have permission to access this page.")
            return redirect('certificates:dashboard')  # Namespaced URL
        return wrapper
    return decorator