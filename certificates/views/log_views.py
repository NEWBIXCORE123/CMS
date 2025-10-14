from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from certificates.models import ActivityLog

@login_required
def activity_logs(request):
    logs_qs = ActivityLog.objects.order_by('-created_at')

    # Count failed login attempts
    failed_counts = (
        ActivityLog.objects
        .filter(action__icontains="failed login attempt")
        .values('user__username')
        .annotate(failed_times=Count('id'))
    )
    failed_dict = {f['user__username'] or 'Anonymous': f['failed_times'] for f in failed_counts}

    # GET filters
    search = request.GET.get('search', '').strip().lower()
    date = request.GET.get('date', '').strip()
    log_type = request.GET.get('type', '').strip().lower()

    logs_list = []
    for log in logs_qs:
        # Determine simple type
        action_lower = (log.action or "").lower()
        if "failed" in action_lower:
            simple_type = "Failed"
        elif "logout" in action_lower or "logged out" in action_lower:
            simple_type = "Logout"
        elif "login" in action_lower or "logged in" in action_lower:
            simple_type = "Login"
        elif any(keyword in action_lower for keyword in ["create", "created", "added", "generated", "new"]):
            simple_type = "Create"
        else:
            simple_type = "Other"

        log.simple_type = simple_type  # add attribute for template

       # Filter by log_type (from dropdown)
        if log_type:
            type_map = {'security': 'failed'}
            mapped_type = type_map.get(log_type, log_type).lower()
            if simple_type.lower() != mapped_type:
                continue


        # Filter by search
        if search:
            # Check if search matches a simple_type
            type_map = {'security': 'failed'}
            search_type = type_map.get(search, search)
            simple_types = ['login', 'logout', 'failed', 'create', 'other']
            if search_type in simple_types and simple_type.lower() != search_type:
                continue
            elif search_type not in simple_types:
                # Fallback to searching action, username, or full name
                if not (
                    search in action_lower or
                    (log.user and search in log.user.username.lower()) or
                    (log.user and log.user.first_name and search in log.user.first_name.lower()) or
                    (log.user and log.user.last_name and search in log.user.last_name.lower())
                ):
                    continue

        # Filter by date
        if date and log.created_at.date().isoformat() != date:
            continue

        logs_list.append(log)

    # Pagination per filtered logs
    paginator = Paginator(logs_list, 9)
    page_number = request.GET.get('page') or 1
    logs = paginator.get_page(page_number)

    return render(request, "certificates/activity_logs.html", {
        "logs": logs,
        "failed_dict": failed_dict,
        "search": search,
        "date": date,
        "log_type": log_type,
    })
