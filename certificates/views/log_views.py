from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from certificates.models import ActivityLog

@login_required
def activity_logs(request):
    # Order by newest first
    logs_qs = ActivityLog.objects.order_by('-created_at')

    # GET filters
    search = request.GET.get('search', '').strip().lower()
    date = request.GET.get('date', '').strip()
    log_type = request.GET.get('type', '').strip().lower()

    filtered_logs = []

    for log in logs_qs:
        action_lower = (log.action or "").lower()

        # Determine simple_type
        if "failed login attempt" in action_lower:
            simple_type = "Failed"
        elif "logged out" in action_lower or "logout" in action_lower:
            simple_type = "Logout"
        elif "logged in" in action_lower or "login" in action_lower:
            simple_type = "Login"
        elif any(keyword in action_lower for keyword in ["create", "created", "added", "generated", "new"]):
            simple_type = "Create"
        else:
            simple_type = "Other"

        log.simple_type = simple_type  # add attribute for template

        # Filter by log_type (dropdown)
        if log_type:
            type_map = {'security': 'failed'}
            mapped_type = type_map.get(log_type, log_type)
            if simple_type.lower() != mapped_type:
                continue

        # Filter by search
        if search:
            if search in ["login", "logout", "failed", "create", "other"]:
                if simple_type.lower() != search:
                    continue
            else:
                if not (
                    search in action_lower
                    or (log.user and search in log.user.username.lower())
                    or (log.user and log.user.first_name and search in log.user.first_name.lower())
                    or (log.user and log.user.last_name and search in log.user.last_name.lower())
                ):
                    continue

        # Filter by date
        if date:
            if log.created_at.date().isoformat() != date:
                continue

        filtered_logs.append(log)

    # Pagination
    paginator = Paginator(filtered_logs, 9)
    page_number = request.GET.get('page') or 1
    logs = paginator.get_page(page_number)

    # Failed login counts for display (optional)
    failed_counts = (
        ActivityLog.objects
        .filter(action__icontains="failed login attempt")
        .values('user__username')
        .annotate(failed_times=Count('id'))
    )
    failed_dict = {f['user__username'] or 'Anonymous': f['failed_times'] for f in failed_counts}

    return render(request, "certificates/activity_logs.html", {
        "logs": logs,
        "failed_dict": failed_dict,
        "search": search,
        "date": date,
        "log_type": log_type,
    })
