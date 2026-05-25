"""Helpers de presentacion para tablas administrativas.

Trazabilidad:
servicios devuelven filas dict -> vistas llaman `display_columns` ->
`shared/table.html` renderiza solo columnas permitidas y ordenadas.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.core.db import list_columns_from_rows

DEFAULT_HIDDEN_COLUMNS = {
    "_actions",
    "_pk",
    "_row_note",
    "_row_status",
    "created_by",
    "created_by_id",
    "created_by_user_id",
    "issued_by_user_id",
    "decided_by_user_id",
    "filed_by_user_id",
    "password",
    "password_hash",
    "updated_at",
}


PREFERRED_COLUMNS = {
    "AuditLog": ["created_at", "action", "entity_table", "entity_pk", "user_id", "ip_address"],
    "Category": ["name", "gender", "mode", "torneo", "description"],
    "Court": ["name", "tournament_surface", "surface", "surface_matches", "capacity", "indoor", "location"],
    "Entry": ["torneo", "category_id", "categoria", "subcategory_id", "cuadro", "team_id", "equipo", "seed", "ranking_at_entry", "draw_size", "available_slots"],
    "InfractionType": ["code", "name", "category", "default_sanction_type", "description"],
    "Injury": ["jugador", "tipo_lesion", "injury_date", "recovery_date", "active", "assigned_at", "description"],
    "Match": ["torneo", "categoria", "cuadro", "ronda", "fecha_partido", "cancha", "jugador_a", "jugador_b", "estado"],
    "MatchParticipant": ["side", "team_id", "sets_won", "games_won", "points_won", "is_winner"],
    "MatchSet": ["set_number", "team_a_games", "team_b_games", "tie_break_a", "tie_break_b", "winner_team_id"],
    "Official": ["first_name", "last_name", "nationality", "official_type", "certification_level", "license_number", "is_active"],
    "Player": ["first_name", "last_name", "country_code", "gender", "hand", "birth_date", "turned_pro_year"],
    "Round": ["round_name", "round_number", "best_of_sets", "subcategory_id", "cuadro", "category_id", "categoria", "torneo", "description"],
    "Sanction": [
        "id",
        "codigo_partido",
        "sanction_type",
        "jugador",
        "infraccion",
        "penalty_points",
        "penalty_games",
        "fine_amount",
        "currency",
        "is_active",
        "issued_at",
        "notes",
    ],
    "SanctionAppeal": ["id", "sanction_id", "status", "filed_by_player_id", "filed_at", "decision", "decided_at", "notes"],
    "Session": ["name", "start_datetime", "end_datetime", "status", "tournament_id", "notes"],
    "SubCategory": ["name", "category_id", "categoria", "torneo", "draw_size", "description"],
    "Team": ["name", "notes"],
    "Tournament": ["name", "year", "status", "start_date", "end_date", "location", "surface", "description"],
    "UserAccount": ["email", "full_name", "phone", "is_active"],
    "ViolationType": ["code", "name", "category", "default_sanction_type", "description"],
}


SECTION_TABLES = {
    "ranking": "Ranking",
    "coaches": "Coach",
    "injuries": "Injury",
    "matches": "Match",
    "Participantes": "MatchParticipant",
    "Sets y marcador": "MatchSet",
    "Juegos y puntos": "MatchGame",
    "Estadisticas": "MatchStatistic",
    "Programacion": "Session",
    "Oficiales asignados": "Official",
    "Sanciones relacionadas": "Sanction",
}


def display_columns(
    rows: list[Mapping[str, Any]],
    fallback_table: str | None = None,
    *,
    preferred: list[str] | None = None,
    hidden: set[str] | None = None,
) -> list[str]:
    """Devuelve columnas relevantes, respetando el orden preferido si existen."""

    available = list_columns_from_rows(rows, fallback_table)
    if not available:
        return []

    hidden_columns = {column.lower() for column in (hidden or DEFAULT_HIDDEN_COLUMNS)}
    available_by_lower = {column.lower(): column for column in available}
    preferred_columns = preferred or PREFERRED_COLUMNS.get(fallback_table or "", [])

    ordered = [
        available_by_lower[column.lower()]
        for column in preferred_columns
        if column.lower() in available_by_lower and column.lower() not in hidden_columns
    ]
    ordered_keys = {column.lower() for column in ordered}
    remaining = [
        column
        for column in available
        if column.lower() not in ordered_keys and column.lower() not in hidden_columns
    ]
    return ordered + remaining[: max(0, 8 - len(ordered))]


def columns_for_section(section_title: str, rows: list[Mapping[str, Any]], table: str | None = None) -> list[str]:
    """Mapea secciones operativas a columnas preferidas de su tabla origen."""

    return display_columns(rows, table or SECTION_TABLES.get(section_title))
