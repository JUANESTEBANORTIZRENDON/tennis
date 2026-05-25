"""Lecturas publicas para la landing sin requerir sesion."""

from __future__ import annotations

from datetime import date, datetime

from apps.core.db import get_value, row_identifier
from apps.core.procedures import fetch_stored_function_value, stored_select_by_id, stored_select_table


ACTIVE_STATUSES = ("active", "activo", "vigente", "ongoing", "en curso", "scheduled", "programado")


def _to_date(value) -> date | None:
    """Convierte un valor (string o date) a datetime.date."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        clean_value = value.strip()
        if not clean_value:
            return None
        try:
            return date.fromisoformat(clean_value[:10])
        except (ValueError, AttributeError):
            try:
                return datetime.fromisoformat(clean_value.replace("Z", "+00:00")).date()
            except (ValueError, AttributeError):
                return None
    return None


def _pick(row: dict, *candidates: str, default=None):
    return get_value(row, *candidates, default=default)


def _format_player(row: dict) -> dict:
    """Reduce una fila Player a los campos visibles publicamente."""

    first_name = _pick(row, "first_name", "name", default="")
    last_name = _pick(row, "last_name", default="")
    full_name = " ".join(part for part in [first_name, last_name] if part).strip() or _pick(row, "full_name", "name", default="Jugador")
    return {
        "id": row_identifier(row, "player_id"),
        "name": full_name,
        "country": _pick(row, "country", "nationality", "country_code", default="-"),
        "ranking": _pick(row, "ranking", "rank", "current_ranking", default="-"),
        "hand": _pick(row, "playing_hand", "dominant_hand", "hand", default="-"),
    }


def _status_from_dates(row: dict) -> str:
    """Deriva estado del torneo si la tabla no trae estado explicito."""

    explicit_status = _pick(row, "status", "state")
    if explicit_status:
        return str(explicit_status)

    today = date.today()
    start_date = _to_date(_pick(row, "start_date"))
    end_date = _to_date(_pick(row, "end_date"))
    if start_date and end_date:
        if start_date <= today <= end_date:
            return "Vigente"
        if end_date < today:
            return "Finalizado"
        if start_date > today:
            return "Proximo"
    return "Sin estado"


def _format_tournament(row: dict) -> dict:
    """Reduce una fila Tournament a una tarjeta publica."""

    return {
        "id": row_identifier(row, "tournament_id"),
        "name": _pick(row, "name", "tournament_name", default="Torneo"),
        "year": _pick(row, "year", default="-"),
        "dates": f"{_pick(row, 'start_date', default='-')} - {_pick(row, 'end_date', default='-')}",
        "location": _pick(row, "location", default="-"),
        "surface": _pick(row, "surface", default="-"),
        "status": _status_from_dates(row),
        "description": _pick(row, "description", default="Información resumida del torneo."),
    }


def public_tournaments(limit: int = 50) -> list[dict]:
    """Devuelve todos los torneos publicables, incluidos finalizados y proximos."""
    rows = stored_select_table("Tournament", order_by_candidates=["start_date", "year", "name", "id"], limit=limit)
    return [_format_tournament(row) for row in rows]


def public_tournament_detail(tournament_id: str | None) -> dict | None:
    """Detalle publico de un torneo seleccionado."""

    if not tournament_id:
        return None
    row = stored_select_by_id("Tournament", tournament_id, ["tournament_id", "id"])
    return _format_tournament(row) if row else None


def public_tournament_bracket(tournament_id: str | int | None) -> dict:
    """Bracket público de un torneo."""

    try:
        selected_id = int(tournament_id) if tournament_id not in (None, "") else None
    except (TypeError, ValueError):
        selected_id = None
    value = fetch_stored_function_value("sp_tournament_bracket_json", [selected_id])
    return value if isinstance(value, dict) else {"tournament": {}, "brackets": []}


def public_players(search: str | None = None, limit: int = 12) -> list[dict]:
    """Lista jugadores para consulta publica en la landing."""
    rows = stored_select_table("Player", search=search, order_by_candidates=["last_name", "first_name", "name", "id"], limit=limit)
    return [_format_player(row) for row in rows]


def public_player_detail(player_id: str | None) -> dict | None:
    """Detalle publico de un jugador seleccionado."""

    if not player_id:
        return None
    row = stored_select_by_id("Player", player_id, ["player_id", "id"])
    return _format_player(row) if row else None


def public_summary() -> dict:
    """Resumen agregado usado por los contadores y listados de la landing."""

    tournaments = public_tournaments()
    active_count = len([tournament for tournament in tournaments if tournament["status"].lower() in ACTIVE_STATUSES])
    return {
        "active_tournaments": active_count,
        "total_tournaments": len(tournaments),
        "visible_players": len(public_players(limit=200)),
        "tournaments": tournaments,
    }
