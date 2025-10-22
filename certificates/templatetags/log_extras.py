from django import template

register = template.Library()

@register.filter
def simple_type(action):
    """Categorize log actions into simplified types for UI display."""
    if not action:
        return "Other"

    action_lower = action.lower()

    # --- FAILED LOGIN / SECURITY (check first to avoid "login" match) ---
    if "failed login" in action_lower or "unauthorized" in action_lower or "security" in action_lower:
        return "Failed"

    # --- LOGIN ---
    if "logged in" in action_lower or "login" in action_lower:
        return "Login"

    # --- LOGOUT ---
    if "logged out" in action_lower or "logout" in action_lower:
        return "Logout"

    # --- REISSUE ---
    if "reissue" in action_lower or "reissued" in action_lower:
        return "Reissue"

    # --- CREATE ---
    if "create" in action_lower or "created" in action_lower or "added" in action_lower or "generated" in action_lower:
        return "Create"

    # --- DELETE / REMOVED ---
    if "delete" in action_lower or "removed" in action_lower:
        return "Delete"

    # --- UPDATE / EDIT ---
    if "update" in action_lower or "edited" in action_lower or "modified" in action_lower:
        return "Update"

    # Default fallback
    return "Other"
