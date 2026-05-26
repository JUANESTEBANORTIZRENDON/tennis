"""Servicio de partidos y programacion.

Combina procedimientos almacenados para acciones de negocio con lecturas
adaptativas para construir el match center.

Trazabilidad:
`apps.matches.views` valida formularios y entra aqui; este servicio llama
procedimientos como `sp_register_match_point` o funciones JSON como
`sp_match_development_detail_json`, y PostgreSQL mantiene reglas de marcador.
"""

from __future__ import annotations

from apps.core.db import (
    find_column,
    find_first_existing_table,
    get_value,
)
from apps.core.procedures import call_stored_procedure, fetch_stored_function_rows, fetch_stored_function_value, stored_select_by_id, stored_select_table


def list_matches(tournament_id: int | None = None, category_id: int | None = None, round_id: int | None = None) -> list[dict]:
    """Listado de partidos con trazabilidad competitiva."""

    rows = fetch_stored_function_rows("sp_matches_by_structure_json", [tournament_id, category_id, round_id, 300])
    return [row for row in rows if isinstance(row, dict)]


def get_match(match_id: int) -> dict | None:
    """Obtiene un partido por id flexible."""

    return stored_select_by_id("Match", match_id, ["id", "match_id"])


def create_match(data: dict) -> None:
    """Crea partido mediante sp_create_match."""

    call_stored_procedure("sp_create_match", data)


def generate_first_round_matches(tournament_id: int, category_id: int | None = None, subcategory_id: int | None = None, mode: str = "ordered") -> None:
    """Genera partidos de primera ronda dentro de procedimientos almacenados."""

    call_stored_procedure(
        "sp_generate_first_round_matches",
        {"tournament_id": tournament_id, "category_id": category_id, "subcategory_id": subcategory_id, "mode": mode},
    )


def first_round_pairing_board(tournament_id: int | None, category_id: int | None = None, subcategory_id: int | None = None) -> list[dict]:
    """Agrupa inscripciones y partidos existentes para armar la primera ronda visual."""

    if not tournament_id:
        return []
    entries = [
        row
        for row in fetch_stored_function_rows("sp_first_round_entries_json", [tournament_id, category_id, subcategory_id])
        if isinstance(row, dict)
    ]
    matches = [
        row
        for row in fetch_stored_function_rows("sp_first_round_matches_json", [tournament_id, category_id, subcategory_id])
        if isinstance(row, dict)
    ]
    groups: dict[str, dict] = {}
    for row in entries:
        key = str(get_value(row, "subcategory_id"))
        groups.setdefault(
            key,
            {
                "subcategory_id": get_value(row, "subcategory_id"),
                "categoria": get_value(row, "categoria"),
                "cuadro": get_value(row, "cuadro"),
                "draw_size": int(get_value(row, "draw_size", default=0) or 0),
                "entries": [],
                "matches": [],
            },
        )
        groups[key]["entries"].append(row)
    for row in matches:
        key = str(get_value(row, "subcategory_id"))
        groups.setdefault(
            key,
            {
                "subcategory_id": get_value(row, "subcategory_id"),
                "categoria": get_value(row, "categoria"),
                "cuadro": get_value(row, "cuadro"),
                "draw_size": int(get_value(row, "draw_size", default=0) or 0),
                "entries": [],
                "matches": [],
            },
        )
        groups[key]["matches"].append(row)
    board = []
    for group in groups.values():
        choices = [row for row in group["entries"] if not get_value(row, "paired")]
        total_pairs = max(0, int(len(group["entries"]) / 2))
        open_slots = list(range(max(0, total_pairs - len(group["matches"]))))
        group["choices"] = choices
        group["open_slots"] = open_slots
        board.append(group)
    return sorted(board, key=lambda item: (str(item.get("categoria") or ""), str(item.get("cuadro") or "")))


def create_first_round_pairing(data: dict) -> None:
    """Crea una pareja manual de primera ronda para el cuadro seleccionado."""

    call_stored_procedure("sp_create_first_round_pairing", data)


def start_match(match_id: int) -> None:
    """Abre el partido del dia para registrar marcador."""

    call_stored_procedure("sp_start_match", {"match_id": match_id})


def update_match_status(match_id: int, status: str) -> None:
    """Actualiza estado operativo del partido."""

    call_stored_procedure("sp_update_match_status", {"match_id": match_id, "status": status})


def add_match_participant(match_id: int, data: dict) -> None:
    """Agrega equipo participante a un partido."""

    payload = {"match_id": match_id, **data}
    call_stored_procedure("sp_add_match_participant", payload)


def register_match_set(match_id: int, data: dict) -> None:
    """Registra marcador de set mediante procedimiento."""

    payload = {"match_id": match_id, **data}
    call_stored_procedure("sp_register_match_set", payload)


def register_match_point(match_id: int, side: str) -> None:
    """Registra un punto y deja que la base cierre games, sets y partido."""

    call_stored_procedure("sp_register_match_point", {"match_id": match_id, "side": side})


def finish_match(match_id: int, data: dict) -> None:
    """Finaliza partido enviando el equipo ganador."""

    payload = {"match_id": match_id, **data}
    call_stored_procedure("sp_finish_match", payload, aliases={"winning_team_id": ["winning_team_id"]})


def schedule_match(match_id: int, data: dict, user_id: int | None) -> None:
    """Programa partido y conserva quien hizo la programacion."""

    payload = {"match_id": match_id, **data, "created_by": user_id}
    call_stored_procedure("sp_schedule_match", payload, aliases={"datetime": ["scheduled_datetime"]})


def reschedule_match(match_id: int, data: dict, user_id: int | None) -> None:
    """Reprograma partido y conserva quien hizo el cambio."""

    payload = {"match_id": match_id, "user_id": user_id, **data}
    call_stored_procedure("sp_reschedule_match", payload)


def list_sessions() -> list[dict]:
    """Lista sesiones/jornadas usando la tabla disponible."""

    table = find_first_existing_table(["Session", "TournamentSession"])
    return stored_select_table(table or "Session", order_by_candidates=["start_datetime", "id"])


def create_session(data: dict) -> None:
    """Crea sesion de programacion."""

    call_stored_procedure("sp_create_session", data)


def add_match_to_session(data: dict) -> None:
    """Agrega partido a una sesion."""

    call_stored_procedure("sp_add_match_to_session", data)


def _rows_for_match(table_candidates: list[str], match_id: int) -> tuple[str | None, list[dict]]:
    """Busca filas relacionadas al partido en la primera tabla existente."""

    table = find_first_existing_table(table_candidates)
    if not table:
        return None, []
    match_col = find_column(table, ["match_id", "id"] if table == "Match" else ["match_id"])
    if match_col:
        return table, stored_select_table(table, filters={match_col: match_id}, limit=100)
    return table, stored_select_table(table, limit=100)


def match_center(match_id: int) -> dict:
    """Arma las secciones que consume la pantalla match center.

    Cada seccion busca primero la tabla vigente en Neon. La vista agrega las
    columnas con `columns_for_section` y el template solo renderiza filas.
    """

    sections = []
    for title, candidates in [
        ("Participantes", ["MatchParticipant", "MatchTeam", "MatchSide"]),
        ("Sets y marcador", ["MatchSet", "SetScore"]),
        ("Juegos y puntos", ["MatchGame", "MatchPoint"]),
        ("Estadisticas", ["MatchTeamStat", "MatchPlayerStat", "MatchStatistic"]),
        ("Programacion", ["MatchSchedule", "Schedule"]),
        ("Oficiales asignados", ["MatchOfficial", "OfficialAssignment"]),
        ("Sanciones relacionadas", ["Sanction"]),
    ]:
        table, rows = _rows_for_match(candidates, match_id)
        sections.append({"title": title, "table": table, "rows": rows, "columns": []})
    return {"match": get_match(match_id), "sections": sections}


def match_development_detail(match_id: int) -> dict:
    """Devuelve datos consolidados para tablero de desarrollo.

    Origen de datos: `sp_match_development_detail_json(match_id)` consolida
    partido, equipos, sets, games y puntos para `matches/match_play.html`.
    """

    value = fetch_stored_function_value("sp_match_development_detail_json", [match_id])
    detail = value if isinstance(value, dict) else {}
    match = detail.get("match") or {}
    teams = detail.get("teams") or {}
    winner_team_id = get_value(match, "winning_team_id")
    if str(winner_team_id) == str(teams.get("A")):
        detail["winner_name"] = get_value(match, "jugador_a", default="Jugador A")
    elif str(winner_team_id) == str(teams.get("B")):
        detail["winner_name"] = get_value(match, "jugador_b", default="Jugador B")
    else:
        detail["winner_name"] = None
    return detail


def team_choices_for_match(match_id: int) -> list[tuple[int | str, str]]:
    """Equipos inscritos elegibles para el partido segun su ronda."""

    match = get_match(match_id) or {}
    round_id = get_value(match, "round_id")
    rows = fetch_stored_function_rows("sp_entry_options_by_round_json", [round_id])
    choices = [("", "Seleccione un equipo")]
    for row in rows:
        if not isinstance(row, dict):
            continue
        team_id = get_value(row, "team_id")
        if team_id in (None, ""):
            continue
        seed = get_value(row, "seed")
        suffix = f"Siembra {seed}" if seed not in (None, "") else None
        label = " - ".join(str(part) for part in [get_value(row, "equipo"), suffix] if part)
        choices.append((team_id, label or str(team_id)))
    return choices
