from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from certificates.models import ActivityLog


@login_required
def activity_logs(request):
    logs_qs = ActivityLog.objects.select_related("user").order_by("-created_at")

    search = request.GET.get("search", "").strip().lower()
    date = request.GET.get("date", "").strip()
    log_type = request.GET.get("type", "").strip().lower()

    filtered_logs = []

    # Helper to classify each log type
    def classify_action(action_text: str) -> str:
        text = (action_text or "").lower()
        if "failed login attempt" in text:
            return "Failed"
        elif "logged out" in text or "logout" in text:
            return "Logout"
        elif "logged in" in text or "login" in text:
            return "Login"
        elif "reissued" in text or "reissue" in text:
            return "Reissue"
        elif any(k in text for k in ["create", "created", "added", "generated", "new"]):
            return "Create"
        else:
            return "Other"

    for log in logs_qs:
        stype = classify_action(log.action)

        # ✅ Dropdown filter
        if log_type and stype.lower() != log_type:
            continue

        # ✅ Search filter
        if search:
            # Search by type keywords (login, logout, failed, etc.)
            if search in ["login", "logout", "failed", "create", "reissue", "other"]:
                if stype.lower() != search:
                    continue
            else:
                # Search text in action, username, or name
                user_match = (
                    (log.user and search in (log.user.username or "").lower())
                    or (log.user and search in (log.user.first_name or "").lower())
                    or (log.user and search in (log.user.last_name or "").lower())
                )
                if not (search in (log.action or "").lower() or user_match):
                    continue

        # ✅ Date filter
        if date and log.created_at.date().isoformat() != date:
            continue

        filtered_logs.append(log)

    paginator = Paginator(filtered_logs, 9)
    page_number = request.GET.get("page") or 1
    logs = paginator.get_page(page_number)

    # Failed login attempt counter
    failed_counts = (
        ActivityLog.objects.filter(action__icontains="failed login attempt")
        .values("user__username")
        .annotate(failed_times=Count("id"))
    )
    failed_dict = {f["user__username"] or "Anonymous": f["failed_times"] for f in failed_counts}

    return render(
        request,
        "certificates/activity_logs.html",
        {
            "logs": logs,
            "failed_dict": failed_dict,
            "search": search,
            "date": date,
            "log_type": log_type,
        },
    )
