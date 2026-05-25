"""Vistas de autenticacion, 2FA y administracion de usuarios.

La sesion guarda un resumen minimo del usuario: id, email, nombre y rol. Las
operaciones contra Neon se delegan al servicio para mantener las vistas livianas.

Trazabilidad:
`apps.accounts.urls` -> estas vistas -> `apps.accounts.forms` ->
`apps.accounts.services.user_service` -> procedimientos/funciones `sp_*` ->
templates `accounts/*` o `shared/*`.
"""

from __future__ import annotations

import random
import time

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.forms import LoginForm, TwoFactorForm, UserCreateForm, UserPasswordChangeForm
from apps.accounts.services.user_service import authenticate_user, change_user_password, create_user, list_users, role_choices, send_two_factor_code
from apps.audit.services.audit_service import log_action_safe
from apps.core.db import row_identifier
from apps.core.errors import SAFE_EMAIL_ERROR, report_safe_error, safe_operation_message
from apps.core.permissions import WRITE_ROLES, admin_required
from apps.core.presentation import display_columns


def _complete_login(request, user: dict) -> None:
    """Renueva la sesion y deja los datos que usan permisos y navegacion."""

    request.session.flush()
    request.session["user_id"] = user["user_id"]
    request.session["email"] = user["email"]
    request.session["full_name"] = user.get("full_name") or user["email"]
    request.session["role_name"] = user.get("role_name") or "Query User"


def login_view(request):
    """Entrada principal: valida credenciales, filtra roles y dispara 2FA."""

    if request.session.get("user_id"):
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, error = authenticate_user(form.cleaned_data["email"], form.cleaned_data["password"])
        if error:
            messages.error(request, error)
        elif user and user.get("role_name") not in WRITE_ROLES:
            messages.error(request, "El login esta reservado para administradores y directores del torneo.")
        elif settings.EMAIL_2FA_ENABLED:
            code = f"{random.SystemRandom().randrange(100000, 1000000)}"
            request.session["pending_2fa_user"] = user
            request.session["pending_2fa_code"] = code
            request.session["pending_2fa_expires_at"] = int(time.time()) + settings.EMAIL_2FA_TIMEOUT_MINUTES * 60
            try:
                send_two_factor_code(user["email"], user.get("full_name") or user["email"], code)
            except Exception as exc:
                request.session.pop("pending_2fa_user", None)
                request.session.pop("pending_2fa_code", None)
                request.session.pop("pending_2fa_expires_at", None)
                report_safe_error(request, exc, SAFE_EMAIL_ERROR)
            else:
                messages.success(request, "Te enviamos un codigo de verificacion al correo registrado.")
                return redirect("login_verify")
        else:
            _complete_login(request, user)
            return redirect("dashboard")

    return render(request, "accounts/login.html", {"form": form})


def login_verify_view(request):
    """Segundo paso de login cuando el correo de verificacion esta habilitado."""

    pending_user = request.session.get("pending_2fa_user")
    if not pending_user:
        return redirect("login")
    if pending_user.get("role_name") not in WRITE_ROLES:
        request.session.flush()
        messages.error(request, "El login esta reservado para administradores y directores del torneo.")
        return redirect("login")

    form = TwoFactorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expires_at = int(request.session.get("pending_2fa_expires_at", 0))
        expected_code = request.session.get("pending_2fa_code")
        if time.time() > expires_at:
            messages.error(request, "El codigo expiro. Inicia sesion de nuevo.")
            request.session.flush()
            return redirect("login")
        if form.cleaned_data["code"] != expected_code:
            messages.error(request, "Codigo de verificacion invalido.")
        else:
            _complete_login(request, pending_user)
            messages.success(request, "Sesion iniciada correctamente.")
            return redirect("dashboard")

    return render(request, "accounts/verify.html", {"form": form, "email": pending_user.get("email")})


def logout_view(request):
    """Cierra la sesion firmada y devuelve al login."""

    request.session.flush()
    messages.info(request, "Sesion cerrada.")
    return redirect("login")


@admin_required
def user_list_view(request):
    """Listado administrativo de cuentas internas."""

    rows = list_users()
    for row in rows:
        user_id = row_identifier(row, "user_id")
        row["_actions"] = [{"label": "Cambiar contrasena", "url": reverse("user_password_change", args=[user_id])}] if user_id else []
    return render(
        request,
        "shared/entity_list.html",
        {
            "title": "Usuarios",
            "subtitle": "Cuentas internas creadas por administracion.",
            "rows": rows,
            "columns": display_columns(rows, "UserAccount", preferred=["email", "full_name", "phone", "is_active"]),
            "empty_message": "No hay usuarios registrados.",
            "primary_action_label": "Crear usuario",
            "primary_action_url": reverse("user_create"),
        },
    )


@admin_required
def user_create_view(request):
    """Crea usuarios y registra auditoria sin exponer la clave temporal."""

    form = UserCreateForm(request.POST or None, role_choices=role_choices())
    if request.method == "POST" and form.is_valid():
        try:
            create_user(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el usuario"))
        else:
            log_action_safe(request, entity_name="UserAccount", action="create", new_value={"email": form.cleaned_data["email"]})
            messages.success(request, "Usuario creado. Entrega la contrasena temporal por un canal seguro.")
            return redirect("user_list")
    return render(request, "shared/form_page.html", {"title": "Crear usuario", "form": form, "back_url": reverse("user_list")})


@admin_required
def user_password_change_view(request, user_id: int):
    """Cambia la contrasena de una cuenta usando procedimiento almacenado."""

    form = UserPasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            change_user_password(user_id, form.cleaned_data["password"])
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("cambiar la contrasena"))
        else:
            log_action_safe(request, entity_name="UserAccount", entity_id=user_id, action="password_change")
            messages.success(request, "Contrasena actualizada correctamente.")
            return redirect("user_list")
    return render(request, "shared/form_page.html", {"title": "Cambiar contrasena", "form": form, "back_url": reverse("user_list")})
