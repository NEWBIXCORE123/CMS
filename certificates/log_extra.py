# certificates/templatetags/log_extras.py
from django import template

register = template.Library()

# List of document-related words to detect as "Create" or "Reissue"
DOCUMENTS = ["barangay clearance", "barangay indigency", "barangay certificate"]

@register.filter
def simple_type(action):
    """
    Simplifies action text into one of:
    Login, Logout, Failed, Create, Reissue
    """
    action_lower = action.lower()

    if "login" in action_lower and "failed" not in action_lower:
        return "Login"
    elif "logout" in action_lower:
        return "Logout"
    elif "failed login" in action_lower or "failed" in action_lower:
        return "Failed"
    elif "reissue" in action_lower or "reissued" in action_lower:
        return "Reissue"
    
    # Detect document creation
    for doc in DOCUMENTS:
        if doc in action_lower:
            return "Create"
    
    if "create" in action_lower or "created" in action_lower:
        return "Create"

    return "Other"  # Fallback for undefined actions


@register.filter
def badge_class(action_type):
    """
    Returns the correct badge class for each simplified action type
    """
    mapping = {
        "Login": "badge-login",
        "Logout": "badge-logout",
        "Failed": "badge-failed",
        "Create": "badge-create",
        "Reissue": "badge-reissue",
        "Other": "badge-create",  # default styling
    }

    
    return mapping.get(action_type, "badge-create")
