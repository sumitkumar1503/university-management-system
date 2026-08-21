from accounts.models import ROLE_THEMES, Role


def theme_and_notifications(request):
    """Expose the active UI theme + a few global bits to every template."""
    user = getattr(request, "user", None)
    theme = None
    unread = 0
    if user is not None and user.is_authenticated:
        theme = user.theme
        from .models import Notice
        aud = ["ALL", user.role]
        unread = Notice.objects.filter(audience__in=aud).count()
    return {
        "theme": theme,
        "notice_count": unread,
        "ROLE_THEMES": ROLE_THEMES,
        "Role": Role,
        "brand_name": "University Management System",
        "brand_short": "UMS",
    }
