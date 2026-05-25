"""Permisos y decoradores de acceso del panel interno.

El proyecto usa sesiones firmadas, no el sistema auth completo de Django. Por
eso los permisos leen `role_name` directamente de `request.session`.

Trazabilidad:
login guarda datos en sesion -> decoradores protegen vistas -> context
processor expone permisos -> templates muestran u ocultan acciones.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from django.contrib import messages
from django.shortcuts import redirect

DIRECTOR = "Tournament Director"
ADMINISTRATOR = "Administrator"
ADMINISTRADOR = "Administrador"
QUERY_USER = "Query User"
AUDITOR = "Auditor"

ADMIN_ROLES = {ADMINISTRATOR, ADMINISTRADOR, "Admin"}
DIRECTOR_ROLES = {DIRECTOR, "Director del Torneo", "Director del torneo"}
WRITE_ROLES = ADMIN_ROLES | DIRECTOR_ROLES
AUDIT_ROLES = ADMIN_ROLES | {AUDITOR}
SENSITIVE_ROLES = WRITE_ROLES


def current_user(request) -> dict:
    """Datos minimos del usuario disponibles para plantillas."""

    return {
        "user_id": request.session.get("user_id"),
        "email": request.session.get("email"),
        "full_name": request.session.get("full_name"),
        "role_name": request.session.get("role_name"),
    }


def is_authenticated(request) -> bool:
    """Comprueba si hay usuario cargado en la sesion."""

    return bool(request.session.get("user_id"))


def can_access_internal_panel(request) -> bool:
    """Por ahora solo roles administrativos entran al panel."""
    return request.session.get("role_name") in WRITE_ROLES


def is_admin_role(request) -> bool:
    """True para roles con administracion de sistema."""

    return request.session.get("role_name") in ADMIN_ROLES


def is_director_role(request) -> bool:
    """True para roles de operacion deportiva."""

    return request.session.get("role_name") in DIRECTOR_ROLES


def can_write(request) -> bool:
    """Permiso de escritura usado para mostrar/ocultar formularios."""

    return request.session.get("role_name") in WRITE_ROLES


def can_view_sensitive(request) -> bool:
    """Permite ver campos sensibles como documentos o licencias."""

    return request.session.get("role_name") in SENSITIVE_ROLES


def has_any_role(request, roles: set[str] | tuple[str, ...] | list[str]) -> bool:
    """Comparador auxiliar para permisos puntuales."""

    return request.session.get("role_name") in set(roles)


def login_required(view_func: Callable):
    """Protege vistas internas y expulsa roles de solo consulta."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_authenticated(request):
            return redirect("login")
        if not can_access_internal_panel(request):
            request.session.flush()
            messages.warning(request, "Este acceso esta reservado para administracion del torneo.")
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


def roles_required(*roles: str):
    """Factory de decoradores para restringir por rol."""

    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not is_authenticated(request):
                return redirect("login")
            if request.session.get("role_name") not in roles:
                messages.warning(request, "Tu rol no tiene permiso para acceder a esta seccion.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def director_required(view_func: Callable):
    return roles_required(*WRITE_ROLES)(view_func)


def admin_required(view_func: Callable):
    return roles_required(*ADMIN_ROLES)(view_func)
