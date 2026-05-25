"""Servicio de usuarios: autenticacion, roles y alta de cuentas.

Este modulo adapta el codigo a un esquema Neon que puede variar en nombres de
columnas. Por eso busca columnas candidatas antes de construir SQL.

Trazabilidad:
vistas de `apps.accounts.views` entregan datos validados aqui; este servicio
lee con `stored_select_table`/`sp_authenticate_user_json` y escribe con
`call_stored_procedure`, dejando la regla final en PostgreSQL.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail

from apps.core.db import find_column, get_value
from apps.core.procedures import call_stored_procedure, fetch_stored_function_value, stored_select_table


def _truthy(value: Any) -> bool:
    """Normaliza valores booleanos que pueden venir como texto desde la BD."""

    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().lower() not in {"0", "false", "f", "no", "n", "inactive", "inactivo"}


def _password_matches(raw_password: str, stored_password: str | None) -> bool:
    """Acepta hashes Django y, por compatibilidad, claves planas heredadas."""

    if not stored_password:
        return False
    if raw_password == stored_password:
        return True
    try:
        return check_password(raw_password, stored_password)
    except Exception:
        return False


def authenticate_user(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
    """Devuelve el usuario autenticado o un mensaje listo para mostrar.

    Origen de datos: `sp_authenticate_user_json(email)` trae la cuenta y rol;
    Python solo verifica estado y hash antes de que la vista cree la sesion.
    """

    user = fetch_stored_function_value("sp_authenticate_user_json", [email])
    if not user:
        return None, "Correo o contrasena invalidos."
    if not isinstance(user, dict):
        return None, "Correo o contrasena invalidos."
    if not _truthy(get_value(user, "is_active")):
        return None, "La cuenta esta inactiva."
    if not _password_matches(password, get_value(user, "password_hash")):
        return None, "Correo o contrasena invalidos."

    user["role_name"] = user.get("role_name") or "Query User"
    user["full_name"] = user.get("full_name") or user.get("email")
    return user, None


def list_users() -> list[dict[str, Any]]:
    """Lista cuentas internas para el panel administrador."""

    return stored_select_table("UserAccount", order_by_candidates=["full_name", "email", "user_id"])


def list_roles() -> list[dict[str, Any]]:
    """Lee los roles disponibles desde la tabla Role."""

    return stored_select_table("Role", order_by_candidates=["name", "role_name", "id"])


def role_choices() -> list[tuple[str, str]]:
    """Convierte Role en opciones para formularios."""

    role_id_col = find_column("Role", ["role_id", "id"])
    role_name_col = find_column("Role", ["role_name", "name"])
    if not role_id_col:
        return []
    choices = []
    for role in list_roles():
        role_id = get_value(role, role_id_col)
        role_name = get_value(role, role_name_col) if role_name_col else role_id
        choices.append((str(role_id), str(role_name)))
    return choices


def create_user(data: dict[str, Any]) -> None:
    """Crea cuentas internas exclusivamente mediante procedimiento almacenado.

    Flujo: `UserCreateForm.cleaned_data` -> hash Django -> payload compatible
    con `sp_create_user_account`.
    """

    payload = {
        "email": data["email"],
        "full_name": data["full_name"],
        "phone": data.get("phone"),
        "password_hash": make_password(data["password"]),
        "role_id": data.get("role_id"),
        "is_active": bool(data.get("is_active")),
    }
    call_stored_procedure("sp_create_user_account", payload)


def change_user_password(user_id: int, raw_password: str) -> None:
    """Actualiza la contrasena mediante procedimiento almacenado."""

    call_stored_procedure(
        "sp_update_user_password",
        {"user_id": user_id, "password_hash": make_password(raw_password)},
    )


def send_two_factor_code(email: str, full_name: str, code: str) -> None:
    """Envia el codigo 2FA usando la configuracion SMTP del proyecto."""

    subject = "Codigo de acceso - Victory's"
    body = (
        f"Hola {full_name},\n\n"
        f"Tu codigo de verificacion para Victory's es: {code}\n\n"
        "Este codigo vence pronto. Si no solicitaste el acceso, puedes ignorar este correo."
    )
    send_mail(subject, body, None, [email], fail_silently=False)
