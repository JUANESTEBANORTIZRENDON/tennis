"""Constructores de opciones para formularios.

Los formularios del proyecto piden listas tipo `(valor, etiqueta)`. Este modulo
las arma desde Neon y tolera diferencias de nombres entre tablas equivalentes.

Trazabilidad:
forms -> `form_choices` -> funciones `sp_*_json` o `stored_select_table` ->
Neon. Asi el usuario ve etiquetas legibles y el procedimiento recibe el ID real.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apps.core.db import find_first_existing_table, get_value, row_identifier
from apps.core.procedures import fetch_stored_function_rows, stored_select_table


Choice = tuple[Any, str]


def _blank(label: str) -> Choice:
    return ("", label)


def _safe_rows(table: str, order_by: list[str] | None = None, limit: int = 300) -> list[dict]:
    """Lee filas para selects; si la BD falla devuelve lista vacia."""

    try:
        return stored_select_table(table, order_by_candidates=order_by or ["name", "id"], limit=limit)
    except Exception:
        return []


def _choice_value(row: dict, *candidates: str):
    return row_identifier(row, *candidates)


def _join_label(*parts: Any) -> str:
    clean = [str(part).strip() for part in parts if part not in (None, "")]
    return " - ".join(clean) if clean else "Sin nombre"


def _generic_label(row: dict) -> str:
    value = _choice_value(row)
    name = get_value(row, "name", "round_name", "full_name", "description", "status")
    return _join_label(value, name)


def _choices(
    table: str,
    *,
    blank_label: str,
    order_by: list[str] | None = None,
    value_candidates: tuple[str, ...] = (),
    label_func: Callable[[dict], str] | None = None,
    limit: int = 300,
) -> list[Choice]:
    """Plantilla comun para generar choices desde cualquier tabla.

    Devuelve primero una opcion vacia, luego pares `(id_real, etiqueta_ui)`.
    """

    choices = [_blank(blank_label)]
    for row in _safe_rows(table, order_by, limit):
        value = _choice_value(row, *value_candidates)
        if value is None:
            continue
        label = label_func(row) if label_func else _generic_label(row)
        choices.append((value, label))
    return choices


def tournament_choices() -> list[Choice]:
    return _choices(
        "Tournament",
        blank_label="Seleccione un torneo",
        order_by=["year", "start_date", "name", "id"],
        value_candidates=("tournament_id", "id"),
        label_func=lambda row: _join_label(get_value(row, "id", "tournament_id"), get_value(row, "name"), get_value(row, "year")),
    )


def user_choices() -> list[Choice]:
    def label(row: dict) -> str:
        return _join_label(get_value(row, "id", "user_id"), get_value(row, "full_name", "name"), get_value(row, "email"))

    return _choices("UserAccount", blank_label="Seleccione un usuario", order_by=["full_name", "email", "id"], value_candidates=("user_id", "id"), label_func=label)


def court_choices() -> list[Choice]:
    return _choices(
        "Court",
        blank_label="Seleccione una cancha",
        order_by=["name", "id"],
        value_candidates=("court_id", "id"),
        label_func=lambda row: _join_label(get_value(row, "id", "court_id"), get_value(row, "name"), get_value(row, "surface")),
    )


def category_choices() -> list[Choice]:
    return _choices("Category", blank_label="Seleccione una categoría", order_by=["name", "id"], value_candidates=("category_id", "id"))


def subcategory_choices() -> list[Choice]:
    return _choices("SubCategory", blank_label="Seleccione un cuadro", order_by=["name", "id"], value_candidates=("subcategory_id", "id"))


def round_choices() -> list[Choice]:
    return _choices(
        "Round",
        blank_label="Seleccione una ronda",
        order_by=["round_number", "round_name", "id"],
        value_candidates=("round_id", "id"),
        label_func=lambda row: _join_label(get_value(row, "id", "round_id"), get_value(row, "round_name"), f"Ronda {get_value(row, 'round_number', default='')}".strip()),
    )


def player_choices() -> list[Choice]:
    def label(row: dict) -> str:
        full_name = _join_label(get_value(row, "first_name"), get_value(row, "last_name")).replace(" - ", " ")
        return _join_label(get_value(row, "id", "player_id"), full_name, get_value(row, "country_code", "country"))

    return _choices("Player", blank_label="Seleccione un jugador", order_by=["last_name", "first_name", "id"], value_candidates=("player_id", "id"), label_func=label)


def team_choices() -> list[Choice]:
    return _choices("Team", blank_label="Seleccione un equipo", order_by=["name", "id"], value_candidates=("team_id", "id"))


def coach_choices() -> list[Choice]:
    def label(row: dict) -> str:
        full_name = _join_label(get_value(row, "first_name"), get_value(row, "last_name")).replace(" - ", " ")
        return _join_label(get_value(row, "id", "coach_id"), full_name, get_value(row, "license_number"))

    return _choices("Coach", blank_label="Seleccione un entrenador", order_by=["last_name", "first_name", "id"], value_candidates=("coach_id", "id"), label_func=label)


def match_choices() -> list[Choice]:
    def label(row: dict) -> str:
        return _join_label(get_value(row, "id", "match_id"), get_value(row, "scheduled_datetime", "scheduled_at"), get_value(row, "status"))

    return _choices("Match", blank_label="Seleccione un partido", order_by=["scheduled_datetime", "match_date", "id"], value_candidates=("match_id", "id"), label_func=label)


def official_choices() -> list[Choice]:
    def label(row: dict) -> str:
        full_name = _join_label(get_value(row, "first_name"), get_value(row, "last_name")).replace(" - ", " ")
        return _join_label(get_value(row, "id", "official_id"), full_name, get_value(row, "official_type"))

    return _choices("Official", blank_label="Seleccione un oficial", order_by=["last_name", "first_name", "id"], value_candidates=("official_id", "id"), label_func=label)


def sanction_choices() -> list[Choice]:
    def label(row: dict) -> str:
        subject = get_value(row, "player_id", "team_id", "official_id", default="")
        return _join_label(get_value(row, "id", "sanction_id"), get_value(row, "sanction_type"), subject)

    return _choices("Sanction", blank_label="Seleccione una sanción", order_by=["issued_at", "id"], value_candidates=("sanction_id", "id"), label_func=label)


def violation_type_choices() -> list[Choice]:
    table = find_first_existing_table(["ViolationType", "InfractionType"]) or "ViolationType"
    return _choices(table, blank_label="Seleccione un tipo de violacion", order_by=["name", "id"], value_candidates=("violation_type_id", "infraction_type_id", "id"))


def injury_choices() -> list[Choice]:
    choices = [_blank("Seleccione una lesión existente")]
    try:
        rows = [row for row in fetch_stored_function_rows("sp_injuries_overview_json", [300]) if isinstance(row, dict)]
    except Exception:
        rows = []

    for row in rows:
        injury_id = get_value(row, "injury_id", "id")
        if injury_id in (None, ""):
            continue
        label = _join_label(
            f"L-{injury_id}",
            get_value(row, "tipo_lesion", "name", "description"),
            get_value(row, "jugador", "player_id"),
        )
        choices.append((injury_id, label))
    return choices


def injury_type_choices() -> list[Choice]:
    table = find_first_existing_table(["InjuryType", "InjuryCategory"]) or "InjuryType"
    return _choices(table, blank_label="Seleccione un tipo de lesión", order_by=["name", "id"], value_candidates=("injury_type_id", "id"))


def session_choices() -> list[Choice]:
    table = find_first_existing_table(["Session", "TournamentSession"]) or "Session"
    return _choices(table, blank_label="Seleccione una sesión", order_by=["start_datetime", "id"], value_candidates=("session_id", "id"))


def team_player_map() -> dict[str, list[str]]:
    """Mapa usado en sanciones para filtrar jugadores segun equipo."""

    table = find_first_existing_table(["TeamMember", "TeamPlayer", "PlayerTeam"])
    if not table:
        return {}
    rows = _safe_rows(table, ["team_id", "player_id"], limit=1000)
    mapping: dict[str, list[str]] = {}
    for row in rows:
        team_id = get_value(row, "team_id")
        player_id = get_value(row, "player_id")
        if team_id in (None, "") or player_id in (None, ""):
            continue
        mapping.setdefault(str(team_id), []).append(str(player_id))
    return mapping


def player_belongs_to_team(player_id: str, team_id: int | str) -> bool:
    """Valida la relacion jugador-equipo antes de crear sanciones."""

    players = team_player_map().get(str(team_id), [])
    return str(player_id) in players
