"""Servicio de oficiales.

Trazabilidad:
`officials.views` entrega datos de formularios; este modulo lee la tabla
`Official` y escribe mediante procedimientos almacenados de oficiales.
"""

from __future__ import annotations

from apps.core.procedures import call_stored_procedure, stored_select_table


def list_officials() -> list[dict]:
    """Listado base de oficiales."""

    return stored_select_table("Official", order_by_candidates=["last_name", "first_name", "id"])


def create_official(data: dict) -> None:
    """Crea oficial mediante sp_create_official."""

    call_stored_procedure("sp_create_official", data)


def assign_official_to_match(data: dict, assigned_by_user_id: int | None) -> None:
    """Asigna oficial a partido guardando quien realizo la asignacion."""

    payload = {**data, "assigned_by_user_id": assigned_by_user_id}
    call_stored_procedure("sp_assign_official_to_match", payload)
