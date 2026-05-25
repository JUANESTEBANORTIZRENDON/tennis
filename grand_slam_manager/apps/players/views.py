"""Vistas de jugadores, lesiones, equipos e inscripciones.

Trazabilidad:
`apps.players.urls` -> estas vistas -> formularios del modulo ->
`player_service` -> procedimientos/funciones `sp_*` y tablas deportivas ->
templates `players/*` y `shared/*`.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.audit.services.audit_service import log_action_safe
from apps.core.db import get_value, row_identifier
from apps.core.errors import report_safe_error, safe_operation_message
from apps.core.permissions import director_required, login_required
from apps.core.presentation import columns_for_section, display_columns
from apps.players.forms import CloseInjuryForm, EntryForm, InjuryRegistrationForm, PlayerForm, TeamForm, TeamMemberForm
from apps.players.services import player_service
from apps.tournaments.services import tournament_service


def _selected_int(request, name: str) -> int | None:
    value = request.GET.get(name) or request.POST.get(name)
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _entry_filter_url(base_name: str, **params) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items() if value not in (None, ""))
    base_url = reverse(base_name)
    return f"{base_url}?{query}" if query else base_url


def _entry_structure_context(request) -> dict:
    selected_tournament_id = _selected_int(request, "tournament_id")
    selected_category_id = _selected_int(request, "category_id")
    selected_subcategory_id = _selected_int(request, "subcategory_id")
    tree = tournament_service.category_tree_for_tournament(selected_tournament_id)
    selected_tournament_id = tree.get("selected_tournament_id")
    categories = tree["categories"]
    subcategories = [row for row in tree["subcategories"] if not selected_category_id or str(get_value(row, "category_id")) == str(selected_category_id)]
    tournament_options = [
        {
            "id": get_value(row, "id", "tournament_id"),
            "label": f"{get_value(row, 'name', default='Torneo')} {get_value(row, 'year', default='')}".strip(),
            "selected": str(get_value(row, "id", "tournament_id")) == str(selected_tournament_id),
        }
        for row in tree["tournaments"]
    ]
    category_options = [{"id": "", "label": "Todas las categorias", "selected": selected_category_id is None}]
    category_options += [
        {"id": get_value(row, "id", "category_id"), "label": get_value(row, "name", default="Categoria"), "selected": str(get_value(row, "id", "category_id")) == str(selected_category_id)}
        for row in categories
    ]
    subcategory_options = [{"id": "", "label": "Todos los cuadros", "selected": selected_subcategory_id is None}]
    subcategory_options += [
        {"id": get_value(row, "id", "subcategory_id"), "label": get_value(row, "name", default="Cuadro"), "selected": str(get_value(row, "id", "subcategory_id")) == str(selected_subcategory_id)}
        for row in subcategories
    ]
    return {
        "selected_tournament_id": selected_tournament_id,
        "selected_category_id": selected_category_id,
        "selected_subcategory_id": selected_subcategory_id,
        "tournament_options": tournament_options,
        "category_options": category_options,
        "subcategory_options": subcategory_options,
        "subcategory_choices": tournament_service.choice_rows(subcategories, label_keys=("categoria", "name")),
    }


@login_required
def player_list_view(request):
    """Lista jugadores y prepara enlaces al detalle."""

    rows = player_service.list_players()
    columns = display_columns(rows, "Player")
    for row in rows:
        pk = row_identifier(row, "player_id")
        row["_actions"] = [{"label": "Detalle", "url": reverse("player_detail", args=[pk])}] if pk else []
    return render(
        request,
        "shared/entity_list.html",
        {
            "title": "Jugadores",
            "subtitle": "Listado de jugadores profesionales.",
            "rows": rows,
            "columns": columns,
            "primary_action_label": "Crear jugador",
            "primary_action_url": reverse("player_create"),
            "empty_message": "No hay jugadores registrados.",
            "mask_plain_id": True,
        },
    )


@director_required
def player_create_view(request):
    """Crea jugadores y registra auditoria."""

    form = PlayerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            player_service.create_player(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el jugador"))
        else:
            log_action_safe(request, entity_name="Player", action="create", new_value=form.cleaned_data)
            messages.success(request, "Jugador creado usando sp_create_player.")
            return redirect("player_list")
    return render(request, "shared/form_page.html", {"title": "Crear jugador", "form": form, "back_url": reverse("player_list")})


@login_required
def player_detail_view(request, player_id: str):
    """Detalle de jugador con secciones relacionadas detectadas por servicio."""

    player = player_service.get_player(player_id)
    related = player_service.player_related(player_id)
    player_name = "Jugador"
    if player:
        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip() or player.get("id") or "Jugador"
    return render(
        request,
        "players/player_detail.html",
        {
            "player": player,
            "player_name": player_name,
            "player_columns": display_columns([player], "Player") if player else [],
            "related_sections": [{"key": key, "rows": value, "columns": columns_for_section(key, value)} for key, value in related.items()],
            "mask_plain_id": True,
        },
    )


@login_required
def injury_list_view(request):
    """Lista lesiones activas/historicas segun la tabla disponible."""

    rows = player_service.list_injuries()
    close_url = reverse("injury_close")
    for row in rows:
        injury_id = row_identifier(row, "injury_id")
        is_active = str(row.get("active", "")).lower() in {"true", "1", "si", "active", "activo"}
        row["_actions"] = [{"label": "Cerrar", "url": f"{close_url}?injury_id={injury_id}"}] if injury_id and is_active else []
    return render(
        request,
        "shared/entity_list.html",
        {
            "title": "Lesiones",
            "subtitle": "Estado active/inactive segun la tabla de lesiones o asignaciones.",
            "rows": rows,
            "columns": display_columns(rows, "Injury"),
            "primary_action_label": "Registrar lesion",
            "primary_action_url": reverse("injury_register"),
            "secondary_action_label": "Cerrar lesion",
            "secondary_action_url": reverse("injury_close"),
            "empty_message": "No hay lesiones registradas.",
        },
    )


@director_required
def injury_register_view(request):
    """Registra o asigna lesiones desde un unico formulario."""

    form = InjuryRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            player_service.register_injury(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("registrar la lesion"))
        else:
            log_action_safe(request, entity_name="Injury", action="create_and_assign", new_value=form.cleaned_data)
            messages.success(request, "Lesion registrada usando sp_create_injury y sp_assign_injury_to_player.")
            return redirect("injury_list")
    return render(request, "shared/form_page.html", {"title": "Registrar lesion", "form": form, "back_url": reverse("injury_list")})


@director_required
def injury_close_view(request):
    """Cierra una lesion mediante sp_close_injury."""

    initial = {"injury_id": request.GET.get("injury_id")} if request.GET.get("injury_id") else None
    form = CloseInjuryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            player_service.close_injury(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("cerrar la lesion"))
        else:
            log_action_safe(request, entity_name="Injury", action="close", entity_id=form.cleaned_data.get("injury_id"), new_value=form.cleaned_data)
            messages.success(request, "Lesion cerrada usando sp_close_injury. No hay accion para reactivarla.")
            return redirect("injury_list")
    return render(request, "shared/form_page.html", {"title": "Cerrar lesion", "form": form, "back_url": reverse("injury_list")})


@login_required
def team_list_view(request):
    """Muestra equipos y formularios embebidos de equipo/integrantes."""

    selected_team_id = _selected_int(request, "team_id")
    rows = player_service.list_teams()
    return render(
        request,
        "players/team_list.html",
        {
            "title": "Equipos",
            "subtitle": "Singles debe tener 1 integrante; Doubles debe tener 2.",
            "rows": rows,
            "columns": display_columns(rows, "Team"),
            "team_form": TeamForm(),
            "member_form": TeamMemberForm(
                selected_team_id=selected_team_id,
                player_choices=player_service.available_team_member_player_choices(selected_team_id),
            ),
            "selected_team_id": selected_team_id,
        },
    )


@director_required
def team_create_view(request):
    """Crea equipos sin salir de la pantalla de equipos."""

    form = TeamForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            player_service.create_team(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el equipo"))
        else:
            log_action_safe(request, entity_name="Team", action="create", new_value=form.cleaned_data)
            messages.success(request, "Equipo creado usando sp_create_team.")
    return redirect("team_list")


@director_required
def team_member_add_view(request):
    """Agrega integrantes y advierte si el equipo queda con tamano inusual."""

    selected_team_id = _selected_int(request, "team_id")
    form = TeamMemberForm(request.POST or None, selected_team_id=selected_team_id, player_choices=player_service.available_team_member_player_choices(selected_team_id))
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            player_service.add_team_member(data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("agregar integrante"))
        else:
            count = player_service.team_member_count(data["team_id"])
            if count not in {1, 2}:
                messages.warning(request, "Advertencia: valida si el cuadro es Singles o Doubles; este equipo tiene un numero inusual de integrantes.")
            log_action_safe(request, entity_name="TeamMember", action="create", entity_id=data.get("team_id"), new_value=data)
            messages.success(request, "Integrante agregado usando sp_add_team_member.")
    return redirect("team_list")


@login_required
def entry_list_view(request):
    """Lista inscripciones con cupos disponibles cuando el esquema lo permite."""

    structure = _entry_structure_context(request)
    rows = player_service.list_entries_with_slots(structure["selected_tournament_id"], structure["selected_category_id"], structure["selected_subcategory_id"])
    return render(
        request,
        "players/entry_list.html",
        {
            "title": "Inscripciones",
            "subtitle": "Cupos disponibles = tamaño del cuadro menos inscripciones actuales.",
            "rows": rows,
            "columns": display_columns(rows, "Entry"),
            "entry_form": EntryForm(
                subcategory_choices=structure["subcategory_choices"],
                team_choices=player_service.available_entry_team_choices(structure["selected_subcategory_id"]),
            ),
            "empty_message": "No hay inscripciones registradas.",
            "entry_create_url": _entry_filter_url(
                "entry_create",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
            ),
            **structure,
        },
    )


@director_required
def entry_create_view(request):
    """Crea inscripciones dentro de cuadros competitivos."""

    structure = _entry_structure_context(request)
    form = EntryForm(
        request.POST or None,
        subcategory_choices=structure["subcategory_choices"],
        team_choices=player_service.available_entry_team_choices(structure["selected_subcategory_id"]),
    )
    if request.method == "POST" and form.is_valid():
        try:
            player_service.create_entry(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear la inscripcion"))
        else:
            log_action_safe(request, entity_name="Entry", action="create", new_value=form.cleaned_data)
            messages.success(request, "Inscripcion creada usando sp_create_entry.")
    return redirect(
        _entry_filter_url(
            "entry_list",
            tournament_id=structure["selected_tournament_id"],
            category_id=structure["selected_category_id"],
            subcategory_id=form.cleaned_data.get("subcategory_id") if form.is_valid() else structure["selected_subcategory_id"],
        )
    )

