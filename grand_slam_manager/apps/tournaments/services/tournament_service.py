"""Servicio de torneos y estructura competitiva.

Expone lecturas simples y llamadas a procedimientos almacenados. Cuando aporta
valor de negocio, enriquece filas con columnas calculadas para la UI.

Trazabilidad:
las vistas de `apps.tournaments.views` llaman este modulo; las lecturas salen de
funciones `sp_*_json` o selectores seguros y las escrituras pasan por
`call_stored_procedure`.
"""

from __future__ import annotations

from apps.core.db import get_value
from apps.core.presentation import display_columns
from apps.core.procedures import call_stored_procedure, fetch_stored_function_rows, fetch_stored_function_value, stored_select_by_id, stored_select_table

TOURNAMENT_ALIASES = {
    "id": ["tournament_id"],
    "start": ["start_date"],
    "end": ["end_date"],
}


def list_tournaments() -> list[dict]:
    """Torneos ordenados para listados administrativos."""

    return stored_select_table("Tournament", order_by_candidates=["year", "start_date", "name", "id"])


def get_tournament(tournament_id: int) -> dict | None:
    """Busca un torneo por id flexible."""

    return stored_select_by_id("Tournament", tournament_id, ["id", "tournament_id"])


def create_tournament(data: dict) -> None:
    """Crea torneo usando alias para firmas SQL historicas."""

    call_stored_procedure("sp_create_tournament", data, aliases=TOURNAMENT_ALIASES)


def update_tournament(tournament_id: int, data: dict) -> None:
    """Actualiza torneo enviando id bajo nombres alternativos."""

    payload = {"id": tournament_id, "tournament_id": tournament_id, **data}
    call_stored_procedure("sp_update_tournament", payload, aliases=TOURNAMENT_ALIASES)


def list_courts() -> list[dict]:
    """Lista canchas y calcula si la superficie coincide con el torneo."""

    return [row for row in fetch_stored_function_rows("sp_list_courts_json") if isinstance(row, dict)]


def create_court(data: dict) -> None:
    """Crea cancha mediante procedimiento almacenado."""

    call_stored_procedure("sp_create_court", data)


def category_tree() -> dict:
    """Carga las cuatro tablas que forman la estructura competitiva."""

    return category_tree_for_tournament(None)


def category_tree_for_tournament(tournament_id: int | None = None) -> dict:
    """Carga la estructura competitiva filtrada por torneo seleccionado.

    Origen de datos: `Tournament` para opciones y funciones
    `sp_categories_by_tournament_json`, `sp_subcategories_by_tournament_json`,
    `sp_rounds_by_tournament_json` para las tablas del arbol.
    """

    tournaments = list_tournaments()
    selected_id = tournament_id
    if selected_id is None and tournaments:
        selected_id = get_value(tournaments[0], "id", "tournament_id")

    return {
        "tournaments": tournaments,
        "selected_tournament_id": selected_id,
        "categories": [row for row in fetch_stored_function_rows("sp_categories_by_tournament_json", [selected_id, 300]) if isinstance(row, dict)],
        "subcategories": [row for row in fetch_stored_function_rows("sp_subcategories_by_tournament_json", [selected_id, 300]) if isinstance(row, dict)],
        "rounds": [row for row in fetch_stored_function_rows("sp_rounds_by_tournament_json", [selected_id, 300]) if isinstance(row, dict)],
    }


def choice_rows(rows: list[dict], *, value_key: str = "id", label_keys: tuple[str, ...] = ("name",)) -> list[tuple[int | str, str]]:
    """Convierte filas ya filtradas en choices para formularios."""

    choices = [("", "Seleccione una opcion")]
    for row in rows:
        value = get_value(row, value_key, "id")
        if value in (None, ""):
            continue
        label = " - ".join(str(get_value(row, key)) for key in label_keys if get_value(row, key) not in (None, ""))
        choices.append((value, label or str(value)))
    return choices


def category_columns(rows: list[dict], table: str) -> list[str]:
    """Columnas de tablas del arbol competitivo."""

    return display_columns(rows, table)


def create_category(data: dict) -> None:
    """Crea categoria mediante procedimiento almacenado."""

    call_stored_procedure("sp_create_category", data)


def create_subcategory(data: dict) -> None:
    """Crea cuadro competitivo mediante procedimiento almacenado."""

    call_stored_procedure("sp_create_subcategory", data)


def create_round(data: dict) -> None:
    """Crea ronda respetando la firma de sp_create_round."""

    call_stored_procedure("sp_create_round", data, aliases={"round_name": ["round_name"], "round_number": ["round_number"]})


def generate_rounds_for_tournament(tournament_id: int) -> None:
    """Genera fases del cuadro cuando las inscripciones estan completas."""

    call_stored_procedure("sp_generate_rounds_for_tournament", {"tournament_id": tournament_id})


def tournament_bracket(tournament_id: int | None) -> dict:
    """Estructura de bracket del torneo seleccionado."""

    value = fetch_stored_function_value("sp_tournament_bracket_json", [tournament_id])
    return value if isinstance(value, dict) else {"tournament": {}, "brackets": []}
