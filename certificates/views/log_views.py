from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from certificates.models import ActivityLog

@login_required
def activity_logs(request):
    from django.core.paginator import Paginator
    from django.db.models import Count

    logs_qs = ActivityLog.objects.order_by('-created_at')

    search = request.GET.get('search', '').strip().lower()
    date = request.GET.get('date', '').strip()
    log_type = request.GET.get('type', '').strip().lower()

    filtered_logs = []

    for log in logs_qs:
        action_lower = (log.action or "").lower()

        # Filter by log_type (dropdown)
        if log_type:
            type_map = {'security': 'failed'}
            mapped_type = type_map.get(log_type, log_type)
            # Use template filter instead of setting attribute
            stype = "Other"
            if "failed login attempt" in action_lower:
                stype = "Failed"
            elif "logout" in action_lower:
                stype = "Logout"
            elif "login" in action_lower:
                stype = "Login"
            elif any(k in action_lower for k in ["create", "created", "added", "generated", "new"]):
                stype = "Create"
            if stype.lower() != mapped_type:
                continue

        # Filter by search
        if search:
            if search in ["login", "logout", "failed", "create", "other"]:
                stype = "Other"
                if "failed login attempt" in action_lower:
                    stype = "Failed"
                elif "logout" in action_lower:
                    stype = "Logout"
                elif "login" in action_lower:
                    stype = "Login"
                elif any(k in action_lower for k in ["create", "created", "added", "generated", "new"]):
                    stype = "Create"
                if stype.lower() != search:
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
        if date and log.created_at.date().isoformat() != date:
            continue

        filtered_logs.append(log)

    paginator = Paginator(filtered_logs, 9)
    page_number = request.GET.get('page') or 1
    logs = paginator.get_page(page_number)

    # Failed login counts
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
