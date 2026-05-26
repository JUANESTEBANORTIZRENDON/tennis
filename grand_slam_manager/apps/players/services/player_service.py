"""Servicio de jugadores y competencia individual/equipos.

Agrupa llamadas a procedimientos y consultas adaptativas para tablas que pueden
tener nombres distintos segun la version del esquema Neon.

Trazabilidad:
las vistas de `apps.players.views` llaman estas funciones; las lecturas usan
selectores seguros o funciones `sp_*_json`, y las escrituras van a
procedimientos almacenados que activan triggers de integridad.
"""

from __future__ import annotations

from apps.core.db import (
    find_column,
    find_first_existing_table,
    get_value,
    table_exists,
)
from apps.core.procedures import (
    call_stored_procedure,
    fetch_stored_function_rows,
    fetch_stored_function_value,
    stored_select_by_id,
    stored_select_table,
)


def list_players() -> list[dict]:
    """Listado base de jugadores."""

    return stored_select_table("Player", order_by_candidates=["last_name", "first_name", "id"])


def get_player(player_id: str) -> dict | None:
    """Busca jugador por id de documento o id interno."""

    return stored_select_by_id("Player", player_id, ["id", "player_id"])


def create_player(data: dict) -> None:
    """Crea jugador usando alias de argumentos para el procedimiento."""

    call_stored_procedure(
        "sp_create_player",
        data,
        aliases={
            "doc_type": ["document_type"],
            "bio": ["biography"],
        },
    )


def _latest_injury_id(data: dict):
    """Recupera la lesion mas reciente despues de crearla."""

    injury_id_col = find_column("Injury", ["id", "injury_id"])
    if not injury_id_col:
        return None
    filters = {}
    if find_column("Injury", ["injury_type_id"]):
        filters["injury_type_id"] = data.get("injury_type_id")
    if find_column("Injury", ["injury_date"]):
        filters["injury_date"] = data.get("injury_date")
    rows = stored_select_table("Injury", filters=filters, order_by_candidates=["id"], limit=200)
    if not rows:
        return None
    return get_value(rows[-1], injury_id_col)


def register_injury(data: dict) -> None:
    """Crea lesion si hace falta y la asigna al jugador.

    Flujo: `InjuryRegistrationForm` -> `sp_create_injury` si no existe id ->
    `sp_assign_injury_to_player` para vincular la lesion al jugador.
    """

    injury_id = data.get("injury_id")
    if not injury_id:
        call_stored_procedure("sp_create_injury", data)
        injury_id = _latest_injury_id(data)

    payload = {"player_id": data.get("player_id"), "injury_id": injury_id}
    call_stored_procedure("sp_assign_injury_to_player", payload)


def close_injury(data: dict) -> None:
    """Marca una lesion como cerrada/recuperada."""

    call_stored_procedure("sp_close_injury", data)


def list_injuries() -> list[dict]:
    """Lista la tabla de lesiones disponible en el esquema."""

    return [row for row in fetch_stored_function_rows("sp_injuries_overview_json", [300]) if isinstance(row, dict)]


def player_related(player_id: str) -> dict[str, list[dict]]:
    """Carga secciones relacionadas para la pagina detalle del jugador."""

    sections: dict[str, list[dict]] = {}
    for label, candidates in {
        "ranking": ["PlayerRanking", "Ranking"],
        "coaches": ["PlayerCoach", "Coach"],
        "injuries": ["PlayerInjury", "Injury"],
        "matches": ["MatchParticipant", "PlayerMatch", "Match"],
    }.items():
        table = find_first_existing_table(candidates)
        if not table:
            sections[label] = []
            continue
        player_col = find_column(table, ["player_id", "id"] if label != "matches" else ["player_id"])
        sections[label] = stored_select_table(table, filters={player_col: player_id} if player_col else None, limit=100)
    return sections


def list_teams() -> list[dict]:
    """Lista equipos competitivos."""

    return stored_select_table("Team", order_by_candidates=["name", "id"])


def create_team(data: dict) -> None:
    """Crea equipo mediante procedimiento almacenado."""

    call_stored_procedure("sp_create_team", data)


def add_team_member(data: dict) -> None:
    """Agrega jugador a equipo mediante procedimiento almacenado."""

    call_stored_procedure("sp_add_team_member", data)


def list_coaches() -> list[dict]:
    """Lista entrenadores con usuario, equipo y jugadores asignados."""

    return [row for row in fetch_stored_function_rows("sp_coaches_overview_json", [300]) if isinstance(row, dict)]


def create_coach(data: dict) -> None:
    """Crea entrenador con usuario interno opcional y equipo obligatorio."""

    call_stored_procedure("sp_create_coach", data)


def assign_coach_to_player(data: dict) -> None:
    """Asigna un jugador al entrenador mediante reglas de equipo en BD."""

    call_stored_procedure("sp_assign_coach_to_player", data)


def available_coach_player_choices(coach_id: int | None) -> list[tuple[str, str]]:
    """Jugadores del equipo del entrenador que aun no estan asignados a el."""

    choices: list[tuple[str, str]] = [("", "Seleccione un jugador")]
    rows = fetch_stored_function_rows("sp_available_coach_players_json", [coach_id])
    for row in rows:
        if not isinstance(row, dict):
            continue
        player_id = get_value(row, "player_id")
        if player_id in (None, ""):
            continue
        label = " - ".join(str(part) for part in [player_id, get_value(row, "jugador"), get_value(row, "equipo")] if part not in (None, ""))
        choices.append((str(player_id), label))
    return choices


def create_entry(data: dict) -> None:
    """Inscribe un equipo en un cuadro."""

    call_stored_procedure("sp_create_entry", data, aliases={"seed": ["seed"]})


def add_entry_team_player(data: dict) -> None:
    """Agrega jugador a un equipo que ya esta inscrito en el cuadro indicado."""

    call_stored_procedure("sp_add_entry_team_player", {"role": "Player", **data})


def entered_team_choices(tournament_id: int | None, category_id: int | None, subcategory_id: int | None) -> list[tuple[int | str, str]]:
    """Equipos que ya tienen inscripcion para el filtro de estructura actual."""

    choices: list[tuple[int | str, str]] = [("", "Seleccione un equipo inscrito")]
    rows = fetch_stored_function_rows("sp_entered_teams_by_structure_json", [tournament_id, category_id, subcategory_id, 300])
    for row in rows:
        if not isinstance(row, dict):
            continue
        team_id = get_value(row, "team_id")
        if team_id in (None, ""):
            continue
        label = " - ".join(str(part) for part in [get_value(row, "equipo"), get_value(row, "cuadro"), get_value(row, "jugadores")] if part not in (None, ""))
        choices.append((team_id, label or str(team_id)))
    return choices


def available_entry_player_choices(tournament_id: int | None, team_id: int | None) -> list[tuple[str, str]]:
    """Jugadores disponibles para un equipo inscrito, excluyendo el mismo torneo."""

    choices: list[tuple[str, str]] = [("", "Seleccione un jugador")]
    rows = fetch_stored_function_rows("sp_available_entry_players_json", [tournament_id, team_id, 300])
    for row in rows:
        if not isinstance(row, dict):
            continue
        player_id = get_value(row, "player_id")
        if player_id in (None, ""):
            continue
        label = " - ".join(str(part) for part in [player_id, get_value(row, "jugador"), get_value(row, "pais")] if part not in (None, ""))
        choices.append((str(player_id), label))
    return choices


def available_entry_team_choices(subcategory_id: int | None) -> list[tuple[int | str, str]]:
    """Equipos disponibles para inscribir en el cuadro seleccionado."""

    choices: list[tuple[int | str, str]] = [("", "Seleccione un equipo")]
    rows = fetch_stored_function_rows("sp_available_entry_teams_json", [subcategory_id])
    for row in rows:
        if not isinstance(row, dict):
            continue
        team_id = get_value(row, "team_id")
        if team_id in (None, ""):
            continue
        label = get_value(row, "equipo", default=str(team_id))
        members = get_value(row, "jugadores")
        required = get_value(row, "jugadores_requeridos")
        suffix = f"{members}/{required} jugadores" if members not in (None, "") and required not in (None, "") else None
        choices.append((team_id, " - ".join(str(part) for part in [label, suffix] if part)))
    return choices


def available_team_member_player_choices(team_id: int | None) -> list[tuple[str, str]]:
    """Jugadores que aun no pertenecen al equipo seleccionado."""

    choices: list[tuple[str, str]] = [("", "Seleccione un jugador")]
    rows = fetch_stored_function_rows("sp_available_team_member_players_json", [team_id])
    for row in rows:
        if not isinstance(row, dict):
            continue
        player_id = get_value(row, "player_id")
        if player_id in (None, ""):
            continue
        label = " - ".join(str(part) for part in [player_id, get_value(row, "jugador"), get_value(row, "pais")] if part not in (None, ""))
        choices.append((str(player_id), label))
    return choices


def list_entries_with_slots(tournament_id: int | None = None, category_id: int | None = None, subcategory_id: int | None = None) -> list[dict]:
    """Calcula cupos disponibles si Entry y SubCategory tienen columnas clave.

    Origen de datos: `sp_entries_by_structure_json` ya devuelve torneo,
    categoria, cuadro y cupos; la vista solo decide filtros y columnas.
    """

    return [
        row
        for row in fetch_stored_function_rows("sp_entries_by_structure_json", [tournament_id, category_id, subcategory_id, 300])
        if isinstance(row, dict)
    ]


def team_member_count(team_id: int) -> int:
    """Cuenta integrantes para validar singles/doubles a nivel de UI."""

    return int(fetch_stored_function_value("sp_team_member_count", [team_id]) or 0)
