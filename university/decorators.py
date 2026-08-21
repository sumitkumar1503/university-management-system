from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, "You don't have access to that area.")
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return _wrapped
    return decorator
