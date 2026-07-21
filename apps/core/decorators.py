from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def super_admin_required(view):
    """Permite el acceso solo al Super Admin; el resto vuelve al inicio."""

    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.es_super_admin:
            messages.info(request, "Necesitás permisos de administrador para eso.")
            return redirect("core:home")
        return view(request, *args, **kwargs)

    return _wrapped
