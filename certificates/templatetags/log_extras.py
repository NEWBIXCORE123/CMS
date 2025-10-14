# certificates/templatetags/log_extras.py
from django import template

register = template.Library()

# List of literal documents to detect
DOCUMENTS = ["barangay clearance", "barangay indigency", "barangay certificate"]

@register.filter
def simple_type(action):
    """
    Maps full action text to simplified type for badge and filtering.
    """
    action_lower = action.lower()

    if "failed login" in action_lower:
        return "Failed"
    elif "login" in action_lower or "logged in" in action_lower:
        return "Login"
    elif "logout" in action_lower or "logged out" in action_lower:
        return "Logout"

    # Generic create/update/delete detection
    if "create" in action_lower or "created" in action_lower:
        return "Create"
    elif "update" in action_lower or "updated" in action_lower:
        return "Update"
    elif "delete" in action_lower or "deleted" in action_lower:
        return "Delete"

    return "Other"



@register.filter
def badge_class(action_type):
    """
    Returns the correct badge class for the type.
    """
    mapping = {
        "Login": "badge-login",
        "Logout": "badge-logout",
        "Failed": "badge-failed",  # new distinct class for failed login
        "Create": "badge-create",
        "Update": "badge-update",
        "Delete": "badge-delete",
        "Other": "badge-other",
    }
    return mapping.get(action_type, "badge-other")

@register.filter
def dict_get(d, key):
    return d.get(key, 0)