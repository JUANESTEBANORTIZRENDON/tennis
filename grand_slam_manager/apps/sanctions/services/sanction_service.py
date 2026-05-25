"""Servicio de sanciones y apelaciones.

Trazabilidad:
`sanctions.views` valida formularios; este servicio lee vistas JSON de
sanciones y llama procedimientos `sp_create_sanction`/`sp_create_sanction_appeal`.
"""

from __future__ import annotations

from apps.core.db import find_first_existing_table
from apps.core.procedures import call_stored_procedure, fetch_stored_function_rows, stored_select_table


def list_infraction_types() -> list[dict]:
    """Lista tipos de violacion/infraccion segun la tabla disponible."""

    table = find_first_existing_table(["ViolationType", "InfractionType"])
    return stored_select_table(table or "ViolationType", order_by_candidates=["name", "id"])


def list_sanctions() -> list[dict]:
    """Lista sanciones recientes."""

    rows = fetch_stored_function_rows("sp_sanctions_overview_json", [300])
    return [row for row in rows if isinstance(row, dict)]


def list_appeals() -> list[dict]:
    """Lista apelaciones de sanciones."""

    table = find_first_existing_table(["SanctionAppeal", "Appeal"])
    return stored_select_table(table or "SanctionAppeal", order_by_candidates=["created_at", "id"], limit=200)


def create_sanction(data: dict, user_id: int | None) -> None:
    """Crea sancion guardando el usuario que la registra."""

    payload = {**data, "user_id": user_id}
    call_stored_procedure("sp_create_sanction", payload)


def create_appeal(data: dict, user_id: int | None) -> None:
    """Crea apelacion guardando el usuario que la presenta."""

    payload = {**data, "filed_by_user_id": user_id}
    call_stored_procedure("sp_create_sanction_appeal", payload)
