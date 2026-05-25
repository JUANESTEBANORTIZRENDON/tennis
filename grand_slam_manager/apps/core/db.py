"""Utilidades de bajo nivel para leer el esquema Neon con SQL seguro.

Los servicios usan estas funciones para no depender de nombres exactos de
columnas. Todas las consultas dinamicas pasan por `quote_ident` para proteger
identificadores de tablas/columnas.

Trazabilidad:
servicios -> helpers de este modulo -> cursor Django/PostgreSQL. Esta capa no
renderiza ni decide permisos; solo devuelve filas normalizadas.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable, Mapping

from django.db import connection


def quote_ident(identifier: str) -> str:
    """Escapa identificadores SQL; no se usa para valores de usuario."""

    return '"' + identifier.replace('"', '""') + '"'


def dictfetchall(cursor) -> list[dict[str, Any]]:
    """Convierte un cursor DB-API en lista de diccionarios."""

    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dictfetchone(cursor) -> dict[str, Any] | None:
    """Devuelve una fila como diccionario o None."""

    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


def fetch_all(sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    """Ejecuta SQL parametrizado y devuelve todas las filas."""

    with connection.cursor() as cursor:
        cursor.execute(sql, list(params or []))
        return dictfetchall(cursor)


def fetch_one(sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    """Ejecuta SQL parametrizado y devuelve la primera fila."""

    with connection.cursor() as cursor:
        cursor.execute(sql, list(params or []))
        return dictfetchone(cursor)


def execute(sql: str, params: Iterable[Any] | None = None) -> None:
    """Ejecuta SQL sin resultado esperado."""

    with connection.cursor() as cursor:
        cursor.execute(sql, list(params or []))


@lru_cache(maxsize=256)
def table_exists(table_name: str) -> bool:
    """Cachea si una tabla existe en el esquema actual."""

    row = fetch_one(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = %s
        ) AS exists
        """,
        [table_name],
    )
    return bool(row and row["exists"])


@lru_cache(maxsize=256)
def get_table_columns(table_name: str) -> tuple[str, ...]:
    """Cachea las columnas reales de una tabla."""

    rows = fetch_all(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        [table_name],
    )
    return tuple(row["column_name"] for row in rows)


def find_column(table_name: str, candidates: Iterable[str]) -> str | None:
    """Encuentra la primera columna existente entre varios nombres posibles."""

    columns = get_table_columns(table_name)
    lower_map = {column.lower(): column for column in columns}
    for candidate in candidates:
        found = lower_map.get(candidate.lower())
        if found:
            return found
    return None


def find_first_existing_table(candidates: Iterable[str]) -> str | None:
    """Encuentra la primera tabla disponible entre alternativas de esquema."""

    for table in candidates:
        if table_exists(table):
            return table
    return None


def list_columns_from_rows(rows: list[Mapping[str, Any]], fallback_table: str | None = None) -> list[str]:
    """Define columnas para tablas HTML, ignorando llaves internas de UI."""

    ignored = {"_actions", "_row_status", "_row_note", "_pk"}
    if rows:
        return [column for column in rows[0].keys() if column not in ignored]
    if fallback_table and table_exists(fallback_table):
        return list(get_table_columns(fallback_table))
    return []


def select_table(
    table_name: str,
    *,
    filters: Mapping[str, Any] | None = None,
    search: str | None = None,
    order_by_candidates: Iterable[str] | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Selector generico para pantallas CRUD simples.

    Lo usan servicios cuando no existe una funcion almacenada especifica para
    una pantalla; mantiene filtros y orden solo sobre columnas existentes.
    """

    if not table_exists(table_name):
        return []

    columns = get_table_columns(table_name)
    where_sql: list[str] = []
    params: list[Any] = []

    for key, value in (filters or {}).items():
        if value in (None, ""):
            continue
        column = find_column(table_name, [key])
        if column:
            where_sql.append(f"{quote_ident(column)} = %s")
            params.append(value)

    if search:
        search_columns = list(columns)[:8]
        if search_columns:
            where_sql.append(
                "(" + " OR ".join(f"CAST({quote_ident(col)} AS TEXT) ILIKE %s" for col in search_columns) + ")"
            )
            params.extend([f"%{search}%"] * len(search_columns))

    order_clause = ""
    for candidate in order_by_candidates or []:
        column = find_column(table_name, [candidate])
        if column:
            order_clause = f" ORDER BY {quote_ident(column)}"
            break

    where_clause = " WHERE " + " AND ".join(where_sql) if where_sql else ""
    sql = f"SELECT * FROM {quote_ident(table_name)}{where_clause}{order_clause} LIMIT %s"
    params.append(int(limit))
    return fetch_all(sql, params)


def select_by_id(table_name: str, object_id: Any, id_candidates: Iterable[str] | None = None) -> dict[str, Any] | None:
    """Busca una fila por id usando nombres de columna flexibles."""

    id_column = find_column(table_name, id_candidates or [f"{table_name.lower()}_id", "id"])
    if not id_column:
        return None
    rows = select_table(table_name, filters={id_column: object_id}, limit=1)
    return rows[0] if rows else None


def safe_count(table_name: str, filters: Mapping[str, Any] | None = None) -> int:
    """Cuenta filas sin fallar si la tabla o columnas no existen."""

    if not table_exists(table_name):
        return 0
    where_sql: list[str] = []
    params: list[Any] = []
    for key, value in (filters or {}).items():
        column = find_column(table_name, [key])
        if column:
            where_sql.append(f"{quote_ident(column)} = %s")
            params.append(value)
    where_clause = " WHERE " + " AND ".join(where_sql) if where_sql else ""
    row = fetch_one(f"SELECT COUNT(*) AS total FROM {quote_ident(table_name)}{where_clause}", params)
    return int(row["total"]) if row else 0


def get_value(row: Mapping[str, Any] | None, *candidates: str, default: Any = None) -> Any:
    """Lee valores de una fila aceptando variantes de nombre de columna."""

    if not row:
        return default
    lower_map = {str(key).lower(): key for key in row.keys()}
    for candidate in candidates:
        key = lower_map.get(candidate.lower())
        if key is not None:
            return row.get(key)
    return default


def row_identifier(row: Mapping[str, Any], *candidates: str) -> Any:
    """Extrae el identificador mas probable de una fila generica."""

    value = get_value(row, *candidates, "id", "pk")
    if value is not None:
        return value
    for key, value in row.items():
        if str(key).lower().endswith("_id"):
            return value
    return None
