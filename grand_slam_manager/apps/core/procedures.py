"""Puente generico hacia procedimientos almacenados de PostgreSQL/Neon.

Este modulo no define una clase; funciona como capa comun para que los
servicios de la aplicacion ejecuten procedimientos `sp_*` sin repetir logica de
conexion, ordenamiento de parametros ni conversiones de datos.

Flujo de escritura:

1. Una vista valida un formulario y entrega `form.cleaned_data` a un servicio.
2. El servicio llama `call_stored_procedure("sp_nombre", data)`.
3. Este modulo consulta `pg_proc` para conocer los parametros IN reales del
   procedimiento en el esquema actual.
4. Los valores del formulario se ordenan para coincidir con esa firma SQL.
5. Se arma un `CALL "sp_nombre"(%s, ...)` parametrizado y se ejecuta con el
   cursor de Django.
6. PostgreSQL ejecuta el procedimiento y sus triggers asociados.

Procedimientos invocados desde los servicios actuales:

- Torneos: `sp_create_tournament`, `sp_update_tournament`,
  `sp_create_court`, `sp_create_category`, `sp_create_subcategory`,
  `sp_create_round`.
- Jugadores/equipos: `sp_create_player`, `sp_create_injury`,
  `sp_assign_injury_to_player`, `sp_close_injury`, `sp_create_team`,
  `sp_add_team_member`, `sp_create_entry`.
- Partidos/programacion: `sp_create_match`, `sp_add_match_participant`,
  `sp_register_match_set`, `sp_finish_match`, `sp_schedule_match`,
  `sp_reschedule_match`, `sp_create_session`, `sp_add_match_to_session`.
- Oficiales: `sp_create_official`, `sp_assign_official_to_match`.
- Sanciones: `sp_create_sanction`, `sp_create_sanction_appeal`.
- Auditoria: `sp_create_audit_log`.

Si se agrega un nuevo procedimiento al sistema, lo normal es crear una funcion
en el servicio del modulo correspondiente y llamarlo mediante
`call_stored_procedure`. Cuando el cambio afecta la firma SQL, debe versionarse
con una migracion `RunSQL` en `apps/core/migrations/`.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
import json
from typing import Any, Iterable

from django.db import connection
from psycopg.types.json import Jsonb

from apps.core.db import dictfetchall, fetch_one, quote_ident


def _clean_arg_name(name: str) -> str:
    """Quita prefijos frecuentes de parametros SQL: p_, in_ o v_."""

    lowered = name.lower()
    for prefix in ("p_", "in_", "v_"):
        if lowered.startswith(prefix):
            return lowered[len(prefix):]
    return lowered


def _lookup_value(arg_name: str, data: Mapping[str, Any], aliases: Mapping[str, Iterable[str]] | None = None) -> Any:
    """Busca en el payload el valor que corresponde a un argumento SQL.

    El procedimiento puede usar nombres como `p_start`, mientras que el
    formulario usa `start_date`. Para cubrir esas diferencias se revisan:

    - El nombre exacto del argumento SQL.
    - El nombre sin prefijos comunes (`p_`, `in_`, `v_`).
    - Alias definidos por el servicio que invoca el procedimiento.
    """

    aliases = aliases or {}
    keys = {str(key).lower(): key for key in data.keys()}
    candidates = [arg_name, _clean_arg_name(arg_name)]
    candidates.extend(aliases.get(arg_name, []))
    candidates.extend(aliases.get(_clean_arg_name(arg_name), []))

    for candidate in candidates:
        key = keys.get(str(candidate).lower())
        if key is not None:
            value = data[key]
            return None if value == "" else value
    return None


def _coerce_value(arg_name: str, value: Any) -> Any:
    """Convierte payloads de detalles a JSONB cuando el procedimiento lo espera."""

    if value == "":
        return None
    normalized = _clean_arg_name(arg_name)
    if "details" in normalized and value is not None:
        if isinstance(value, (dict, list)):
            return Jsonb(value)
        if isinstance(value, str):
            try:
                return Jsonb(json.loads(value))
            except json.JSONDecodeError:
                return Jsonb({"value": value})
    return value


@lru_cache(maxsize=128)
def get_procedure_args(procedure_name: str) -> tuple[str, ...]:
    """Lee y cachea los argumentos IN de un procedimiento del esquema actual.

    La consulta usa `pg_proc` y `pg_namespace`, por eso no es necesario duplicar
    en Python la firma de cada procedimiento almacenado. Si Neon cambia el orden
    o nombre de parametros, el helper toma la firma vigente en la base.
    """

    row = fetch_one(
        """
        SELECT
            COALESCE(p.proargnames, ARRAY[]::text[]) AS arg_names,
            COALESCE(p.proargmodes, ARRAY[]::"char"[]) AS arg_modes,
            p.pronargs
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = current_schema()
          AND p.proname = %s
          AND p.prokind = 'p'
        ORDER BY p.oid::regprocedure::text
        LIMIT 1
        """,
        [procedure_name],
    )
    if not row:
        return tuple()

    names = list(row.get("arg_names") or [])
    modes = list(row.get("arg_modes") or [])
    if not names:
        return tuple()

    in_names: list[str] = []
    for index, name in enumerate(names):
        mode = modes[index] if index < len(modes) else "i"
        if name and mode in {"i", "b", "v"}:
            in_names.append(name)
    return tuple(in_names)


def call_procedure(sql: str, params: Iterable[Any] | None = None) -> None:
    """Ejecuta un `CALL` ya construido usando parametros seguros."""

    with connection.cursor() as cursor:
        cursor.execute(sql, list(params or []))


def _unwrap_function_row(row: dict[str, Any]) -> Any:
    if len(row) == 1:
        value = next(iter(row.values()))
        if isinstance(value, str) and value[:1] in {"{", "["}:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    return row


def fetch_stored_function_rows(function_name: str, params: Iterable[Any] | None = None) -> list[Any]:
    """Ejecuta una funcion almacenada y devuelve sus filas.

    Esta es la entrada de lectura usada por servicios cuando Neon ya expone una
    funcion `sp_*_json`; los templates nunca llaman SQL directamente.
    """

    values = list(params or [])
    placeholders = ",".join(["%s"] * len(values))
    sql = f"SELECT * FROM {quote_ident(function_name)}({placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        return [_unwrap_function_row(row) for row in dictfetchall(cursor)]


def fetch_stored_function_value(function_name: str, params: Iterable[Any] | None = None) -> Any:
    """Ejecuta una funcion almacenada escalar y devuelve el primer valor."""

    rows = fetch_stored_function_rows(function_name, params)
    return rows[0] if rows else None


def stored_select_table(
    table_name: str,
    *,
    filters: Mapping[str, Any] | None = None,
    search: str | None = None,
    order_by_candidates: Iterable[str] | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Lee una tabla mediante funcion almacenada parametrizada.

    Trazabilidad: servicios de dominio -> `sp_select_table_json` -> tabla real
    en Neon -> filas normalizadas para `display_columns` y templates.
    """

    rows = fetch_stored_function_rows(
        "sp_select_table_json",
        [table_name, Jsonb(filters or {}), search, list(order_by_candidates or []), int(limit)],
    )
    return [row for row in rows if isinstance(row, dict)]


def stored_select_by_id(table_name: str, object_id: Any, id_candidates: Iterable[str] | None = None) -> dict[str, Any] | None:
    """Busca una fila por id mediante funcion almacenada."""

    row = fetch_stored_function_value(
        "sp_select_by_id_json",
        [table_name, None if object_id is None else str(object_id), list(id_candidates or [])],
    )
    return row if isinstance(row, dict) else None


def stored_safe_count(table_name: str, filters: Mapping[str, Any] | None = None) -> int:
    """Cuenta filas mediante funcion almacenada."""

    value = fetch_stored_function_value("sp_safe_count", [table_name, Jsonb(filters or {})])
    return int(value or 0)


def call_stored_procedure(
    procedure_name: str,
    data: Mapping[str, Any] | None = None,
    *,
    ordered_values: Iterable[Any] | None = None,
    aliases: Mapping[str, Iterable[str]] | None = None,
) -> None:
    """Ordena datos por firma real y ejecuta el procedimiento almacenado.

    Args:
        procedure_name: Nombre del procedimiento PostgreSQL, por ejemplo
            `sp_create_tournament`.
        data: Diccionario normalmente proveniente de `form.cleaned_data`.
        ordered_values: Lista ya ordenada de valores. Se usa solo si no hay
            `data` o cuando el servicio necesita control total del orden.
        aliases: Mapa para conectar nombres del procedimiento con nombres del
            formulario, por ejemplo `{"datetime": ["scheduled_datetime"]}`.

    La funcion no contiene reglas de negocio concretas. Esas reglas viven en
    los procedimientos de PostgreSQL y en los servicios de cada modulo.
    """

    arg_names = get_procedure_args(procedure_name)
    if arg_names and data is not None:
        values = [_coerce_value(arg_name, _lookup_value(arg_name, data, aliases)) for arg_name in arg_names]
    elif ordered_values is not None:
        values = [None if value == "" else value for value in ordered_values]
    elif data is not None:
        values = [None if value == "" else value for value in data.values()]
    else:
        values = []

    placeholders = ",".join(["%s"] * len(values))
    sql = f"CALL {quote_ident(procedure_name)}({placeholders})"
    call_procedure(sql, values)
