"""CRUD generico para el perfil administrador.

El panel usa funciones y procedimientos almacenados genericos para listar,
crear, actualizar y eliminar filas sin construir SQL directo en las vistas.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from apps.core.db import get_value
from apps.core.procedures import call_stored_procedure, fetch_stored_function_rows, fetch_stored_function_value


def list_admin_tables() -> list[dict[str, Any]]:
    """Tablas disponibles en el esquema actual."""

    return [row for row in fetch_stored_function_rows("sp_admin_tables_json") if isinstance(row, dict)]


def table_columns(table_name: str) -> list[dict[str, Any]]:
    """Metadatos de columnas para formularios dinamicos."""

    return [row for row in fetch_stored_function_rows("sp_admin_table_columns_json", [table_name]) if isinstance(row, dict)]


def table_rows(table_name: str, search: str | None = None) -> list[dict[str, Any]]:
    """Filas de una tabla administrativa."""

    return [row for row in fetch_stored_function_rows("sp_admin_table_rows_json", [table_name, search, 300]) if isinstance(row, dict)]


def primary_key_column(columns: list[dict[str, Any]]) -> str | None:
    """Devuelve la PK real o una columna id como alternativa."""

    for column in columns:
        if get_value(column, "is_primary_key"):
            return str(get_value(column, "column_name"))
    for column in columns:
        name = str(get_value(column, "column_name", default=""))
        if name.lower() == "id" or name.lower().endswith("_id"):
            return name
    return str(get_value(columns[0], "column_name")) if columns else None


def get_admin_row(table_name: str, pk_column: str, pk_value: str) -> dict[str, Any] | None:
    """Obtiene una fila por PK desde funcion almacenada."""

    row = fetch_stored_function_value("sp_admin_row_json", [table_name, pk_column, pk_value])
    return row if isinstance(row, dict) else None


def save_admin_row(table_name: str, pk_column: str, pk_value: str | None, payload: dict[str, Any]) -> None:
    """Crea o actualiza una fila usando procedimiento almacenado."""

    call_stored_procedure(
        "sp_admin_upsert_row",
        ordered_values=[table_name, pk_column, pk_value or "", Jsonb(payload)],
    )


def delete_admin_row(table_name: str, pk_column: str, pk_value: str) -> None:
    """Elimina una fila usando procedimiento almacenado."""

    call_stored_procedure("sp_admin_delete_row", ordered_values=[table_name, pk_column, pk_value])
