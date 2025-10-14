def role_context(request):
    role = None
    user = request.user
    if user.is_authenticated:
        if hasattr(user, 'role'):
            role = user.role
        elif user.is_superuser:
            role = "superadmin"
    return {'role': role}
