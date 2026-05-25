"""Consultas resumidas para el dashboard interno."""

from __future__ import annotations

from apps.core.db import find_column, get_value
from apps.core.procedures import fetch_stored_function_rows, stored_safe_count, stored_select_table
from apps.tournaments.services import tournament_service


def _count_by_status(table_name: str, statuses: list[str]) -> int:
    """Cuenta por estado si existe columna status/state; si no, cuenta todo."""

    status_col = find_column(table_name, ["status", "state"])
    if not status_col:
        return stored_safe_count(table_name)
    rows = stored_select_table(table_name, limit=1000)
    normalized_statuses = {status.lower() for status in statuses}
    return len([row for row in rows if str(get_value(row, status_col, default="")).lower() in normalized_statuses])


def dashboard_metrics() -> dict:
    """Indicadores compactos de operacion para la primera pantalla interna."""

    return {
        "tournaments": stored_safe_count("Tournament"),
        "scheduled_matches": _count_by_status("Match", ["scheduled", "programado"]),
        "players": stored_safe_count("Player"),
        "active_injuries": _count_by_status("Injury", ["active", "activo", "open", "abierto"]),
        "recent_sanctions": stored_safe_count("Sanction"),
    }


def upcoming_matches(limit: int = 8) -> list[dict]:
    """Partidos recientes/proximos que alimentan la tabla del dashboard."""

    return [row for row in fetch_stored_function_rows("sp_dashboard_upcoming_matches_json", [limit]) if isinstance(row, dict)]


def dashboard_tournaments(selected_id: int | None = None) -> tuple[list[dict], int | None]:
    """Opciones de torneo para el diagrama competitivo del dashboard."""

    tournaments = tournament_service.list_tournaments()
    active_id = selected_id
    if active_id is None and tournaments:
        active_id = get_value(tournaments[0], "id", "tournament_id")
    options = [
        {
            "id": get_value(row, "id", "tournament_id"),
            "label": f"{get_value(row, 'name', default='Torneo')} {get_value(row, 'year', default='')}".strip(),
            "selected": str(get_value(row, "id", "tournament_id")) == str(active_id),
        }
        for row in tournaments
    ]
    return options, active_id


def dashboard_bracket(tournament_id: int | None) -> dict:
    """Bracket legible para el tablero principal."""

    return tournament_service.tournament_bracket(tournament_id)
