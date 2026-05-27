"""Vistas operativas de partidos, match center y programacion.

Trazabilidad:
`apps.matches.urls` -> estas vistas -> formularios de match center ->
`match_service` -> procedimientos `sp_*` de partido/programacion -> templates
`matches/*`.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.audit.services.audit_service import log_action_safe
from apps.core.db import get_value, row_identifier
from apps.core.errors import report_safe_error, safe_operation_message
from apps.core.permissions import director_required, login_required
from apps.core.presentation import columns_for_section, display_columns
from apps.matches.forms import (
    FinishMatchForm,
    MatchForm,
    MatchParticipantForm,
    MatchSetForm,
    RescheduleMatchForm,
    ScheduleAssignmentForm,
    ScheduleMatchForm,
    SessionForm,
    SessionMatchForm,
)
from apps.matches.services import match_service
from apps.tournaments.services import tournament_service


def _selected_int(request, name: str) -> int | None:
    value = request.GET.get(name) or request.POST.get(name)
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _filter_url(base_name: str, **params) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items() if value not in (None, ""))
    base_url = reverse(base_name)
    return f"{base_url}?{query}" if query else base_url


def _selected_structure_context(request) -> dict:
    """Filtros comunes de torneo, categoria y cuadro para pantallas operativas."""

    selected_tournament_id = _selected_int(request, "tournament_id")
    selected_category_id = _selected_int(request, "category_id")
    selected_subcategory_id = _selected_int(request, "subcategory_id")
    tree = tournament_service.category_tree_for_tournament(selected_tournament_id)
    selected_tournament_id = tree.get("selected_tournament_id")
    categories = tree["categories"]
    subcategories = [
        row
        for row in tree["subcategories"]
        if not selected_category_id or str(get_value(row, "category_id")) == str(selected_category_id)
    ]
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
        {
            "id": get_value(row, "id", "category_id"),
            "label": get_value(row, "name", default="Categoria"),
            "selected": str(get_value(row, "id", "category_id")) == str(selected_category_id),
        }
        for row in categories
    ]
    subcategory_options = [{"id": "", "label": "Todos los cuadros", "selected": selected_subcategory_id is None}]
    subcategory_options += [
        {
            "id": get_value(row, "id", "subcategory_id"),
            "label": get_value(row, "name", default="Cuadro"),
            "selected": str(get_value(row, "id", "subcategory_id")) == str(selected_subcategory_id),
        }
        for row in subcategories
    ]
    courts = [
        row
        for row in tournament_service.list_courts()
        if not selected_tournament_id or str(get_value(row, "tournament_id")) == str(selected_tournament_id)
    ]
    return {
        "selected_tournament_id": selected_tournament_id,
        "selected_category_id": selected_category_id,
        "selected_subcategory_id": selected_subcategory_id,
        "tournament_options": tournament_options,
        "category_options": category_options,
        "subcategory_options": subcategory_options,
        "court_choices": tournament_service.choice_rows(courts, label_keys=("name", "surface")),
    }


def _structure_context(request) -> dict:
    context = _selected_structure_context(request)
    selected_tournament_id = context["selected_tournament_id"]
    selected_category_id = context["selected_category_id"]
    tree = tournament_service.category_tree_for_tournament(selected_tournament_id)
    rounds = [row for row in tree["rounds"] if not selected_category_id or str(get_value(row, "category_id")) == str(selected_category_id)]
    return {
        **context,
        "round_choices": tournament_service.choice_rows(rounds, label_keys=("cuadro", "round_name")),
    }


@login_required
def match_list_view(request):
    """Lista partidos y enlaza cada fila con su match center."""

    structure = _structure_context(request)
    rows = match_service.list_matches(structure["selected_tournament_id"], structure["selected_category_id"], None)
    columns = display_columns(rows, "Match")
    for row in rows:
        pk = row_identifier(row, "match_id")
        actions = []
        if pk:
            actions.append(
                {
                    "label": "Programar",
                    "url": _filter_url(
                        "schedule_list",
                        tournament_id=get_value(row, "tournament_id"),
                        category_id=get_value(row, "category_id"),
                        subcategory_id=get_value(row, "subcategory_id"),
                    ),
                }
            )
        raw_status = str(get_value(row, "_estado_raw", default=""))
        if pk and raw_status == "Completed":
            actions.append({"label": "Ver resultados", "url": reverse("match_result", args=[pk])})
        if pk and (row.get("can_open_today") or raw_status == "InProgress"):
            actions.append({"label": "Desarrollo", "url": reverse("match_play", args=[pk])})
        row["_actions"] = actions
    return render(
        request,
        "matches/match_list.html",
        {
            "title": "Match Center",
            "subtitle": "Centro operativo de partidos, marcador, programacion y sanciones.",
            "rows": rows,
            "columns": columns,
            "primary_action_url": _filter_url(
                "match_first_round_pairing",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
            ),
            "pairing_random_url": _filter_url(
                "match_generate_first_round",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
                mode="random",
            ),
            "pairing_ordered_url": _filter_url(
                "match_generate_first_round",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
                mode="ordered",
            ),
            "empty_message": "No hay partidos registrados.",
            **structure,
        },
    )


@director_required
def match_generate_first_round_view(request):
    """Genera emparejamientos iniciales del torneo seleccionado."""

    tournament_id = _selected_int(request, "tournament_id")
    category_id = _selected_int(request, "category_id")
    subcategory_id = _selected_int(request, "subcategory_id")
    mode = request.GET.get("mode") or request.POST.get("mode") or "ordered"
    if request.method == "POST" and tournament_id:
        try:
            match_service.generate_first_round_matches(tournament_id, category_id, subcategory_id, mode)
        except Exception as exc:
            message = str(exc)
            if "draw_not_full" in message:
                report_safe_error(request, exc, "Completa las inscripciones del cuadro antes de generar partidos.")
            elif "first_round_missing" in message:
                report_safe_error(request, exc, "Primero genera las rondas del torneo.")
            elif "round_matches_already_exist" in message:
                report_safe_error(request, exc, "La primera ronda ya tiene partidos generados.")
            else:
                report_safe_error(request, exc, safe_operation_message("generar los partidos"))
        else:
            log_action_safe(request, entity_name="Tournament", entity_id=tournament_id, action=f"generate_first_round_{mode}")
            messages.success(request, "Partidos de primera ronda generados.")
    return redirect(
        _filter_url(
            "match_list",
            tournament_id=tournament_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
        )
    )


@director_required
def match_first_round_pairing_view(request):
    """Interfaz visual para construir parejas manuales de primera ronda."""

    structure = _structure_context(request)
    board = match_service.first_round_pairing_board(
        structure["selected_tournament_id"],
        structure["selected_category_id"],
        structure["selected_subcategory_id"],
    )
    for group in board:
        group["create_url"] = _filter_url(
            "match_first_round_pairing_create",
            tournament_id=structure["selected_tournament_id"],
            category_id=structure["selected_category_id"],
            subcategory_id=group.get("subcategory_id"),
        )
    return render(
        request,
        "matches/first_round_pairings.html",
        {
            "title": "Primera ronda",
            "board": board,
            "back_url": _filter_url(
                "match_list",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
            ),
            **structure,
        },
    )


@director_required
def match_first_round_pairing_create_view(request):
    """Guarda una pareja manual de primera ronda desde la vista visual."""

    tournament_id = _selected_int(request, "tournament_id")
    category_id = _selected_int(request, "category_id")
    subcategory_id = _selected_int(request, "subcategory_id")
    if request.method == "POST":
        try:
            match_service.create_first_round_pairing(
                {
                    "subcategory_id": _selected_int(request, "pair_subcategory_id") or subcategory_id,
                    "team_a_id": _selected_int(request, "team_a_id"),
                    "team_b_id": _selected_int(request, "team_b_id"),
                }
            )
        except Exception as exc:
            message = str(exc)
            if "team_already_paired" in message:
                report_safe_error(request, exc, "Ese equipo ya esta emparejado en la primera ronda.")
            elif "same_team_pairing" in message:
                report_safe_error(request, exc, "Selecciona dos equipos diferentes.")
            elif "team_not_entered" in message:
                report_safe_error(request, exc, "Solo puedes emparejar equipos inscritos en ese cuadro.")
            else:
                report_safe_error(request, exc, safe_operation_message("crear el emparejamiento"))
        else:
            log_action_safe(request, entity_name="Match", action="manual_first_round_pairing")
            messages.success(request, "Emparejamiento de primera ronda creado.")
    return redirect(
        _filter_url(
            "match_first_round_pairing",
            tournament_id=tournament_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
        )
    )


@director_required
def match_create_view(request):
    """Crea un partido base."""

    structure = _structure_context(request)
    form = MatchForm(
        request.POST or None,
        round_choices=structure["round_choices"],
        court_choices=structure["court_choices"],
    )
    if request.method == "POST" and form.is_valid():
        try:
            match_service.create_match(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el partido"))
        else:
            log_action_safe(request, entity_name="Match", action="create", new_value=form.cleaned_data)
            messages.success(request, "Partido creado usando sp_create_match.")
        return redirect(
            _filter_url(
                "match_list",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
            )
        )
    return render(request, "shared/form_page.html", {"title": "Crear partido", "form": form, "back_url": reverse("match_list")})


@login_required
def match_center_view(request, match_id: int):
    """Pantalla unica para operar participantes, sets y programacion."""

    center = match_service.match_center(match_id)
    for section in center["sections"]:
        section["columns"] = columns_for_section(section["title"], section["rows"], section.get("table"))
    team_choices = match_service.team_choices_for_match(match_id)
    return render(
        request,
        "matches/match_center.html",
        {
            "center": center,
            "match_id": match_id,
            "match_columns": display_columns([center["match"]], "Match") if center.get("match") else [],
            "participant_form": MatchParticipantForm(team_choices=team_choices),
            "set_form": MatchSetForm(team_choices=team_choices),
            "finish_form": FinishMatchForm(team_choices=team_choices),
            "schedule_form": ScheduleMatchForm(),
            "reschedule_form": RescheduleMatchForm(),
            "schedule_url": reverse("schedule_list"),
        },
    )


def _handle_match_action(request, match_id: int, form_class, service_func, success_message: str, action_name: str, include_user: bool = False):
    """Wrapper comun para acciones POST del match center."""

    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            if include_user:
                service_func(match_id, form.cleaned_data, request.session.get("user_id"))
            else:
                service_func(match_id, form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("ejecutar la accion"))
        else:
            log_action_safe(request, entity_name="Match", entity_id=match_id, action=action_name, new_value=form.cleaned_data)
            messages.success(request, success_message)
    else:
        messages.error(request, "Formulario invalido. Revisa los campos requeridos.")
    return redirect("match_center", match_id=match_id)


def _handle_match_action_to_play(request, match_id: int, form_class, service_func, success_message: str, action_name: str, include_user: bool = False):
    team_choices = match_service.team_choices_for_match(match_id)
    form = form_class(request.POST or None, team_choices=team_choices) if form_class in {MatchSetForm, FinishMatchForm} else form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            if include_user:
                service_func(match_id, form.cleaned_data, request.session.get("user_id"))
            else:
                service_func(match_id, form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("ejecutar la accion"))
        else:
            log_action_safe(request, entity_name="Match", entity_id=match_id, action=action_name, new_value=form.cleaned_data)
            messages.success(request, success_message)
    else:
        messages.error(request, "Formulario invalido. Revisa los campos requeridos.")
    return redirect("match_play", match_id=match_id)


@director_required
def match_add_participant_view(request, match_id: int):
    """Agrega participante al partido."""

    return _handle_match_action(request, match_id, MatchParticipantForm, match_service.add_match_participant, "Participante agregado usando sp_add_match_participant.", "add_participant")


@director_required
def match_register_set_view(request, match_id: int):
    """Registra set del partido."""

    return _handle_match_action(request, match_id, MatchSetForm, match_service.register_match_set, "Set registrado usando sp_register_match_set.", "register_set")


@director_required
def match_finish_view(request, match_id: int):
    """Finaliza partido."""

    return _handle_match_action(request, match_id, FinishMatchForm, match_service.finish_match, "Partido finalizado usando sp_finish_match.", "finish")


@director_required
def match_schedule_view(request, match_id: int):
    """Programa partido usando el usuario actual como responsable."""

    return _handle_match_action(request, match_id, ScheduleMatchForm, match_service.schedule_match, "Partido programado usando sp_schedule_match.", "schedule", include_user=True)


@director_required
def match_reschedule_view(request, match_id: int):
    """Reprograma partido usando el usuario actual como responsable."""

    return _handle_match_action(request, match_id, RescheduleMatchForm, match_service.reschedule_match, "Partido reprogramado usando sp_reschedule_match.", "reschedule", include_user=True)


@login_required
def match_development_list_view(request):
    """Lista partidos operables en tablero de desarrollo."""

    rows = match_service.list_matches()
    rows = [
        row
        for row in rows
        if str(get_value(row, "_estado_raw", default="")).lower() in {"scheduled", "inprogress", "suspended", "completed"}
    ]
    for row in rows:
        pk = row_identifier(row, "match_id")
        raw_status = str(get_value(row, "_estado_raw", default=""))
        actions = []
        if pk and raw_status == "Completed":
            actions.append({"label": "Ver resultados", "url": reverse("match_result", args=[pk])})
        elif pk and (row.get("can_open_today") or raw_status == "InProgress"):
            actions.append({"label": "Abrir tablero", "url": reverse("match_play", args=[pk])})
        row["_actions"] = actions
    return render(
        request,
        "matches/match_development_list.html",
        {
            "rows": rows,
            "columns": display_columns(rows, "Match"),
            "empty_message": "No hay partidos programados para operar.",
        },
    )


@login_required
def match_result_view(request, match_id: int):
    """Resumen de resultado para partidos completados."""

    detail = match_service.match_development_detail(match_id)
    match = detail.get("match") or {}
    sets, score_title = match_service.match_result_score_rows(match_id)
    return render(
        request,
        "matches/match_result.html",
        {
            "match_id": match_id,
            "match": match,
            "sets": sets,
            "set_columns": display_columns(sets, "MatchSet"),
            "score_title": score_title,
            "winner_name": detail.get("winner_name"),
            "detail_url": reverse("match_center", args=[match_id]),
            "back_url": reverse("match_development_list"),
        },
    )


@login_required
def match_play_view(request, match_id: int):
    """Tablero de desarrollo de partido."""

    detail = match_service.match_development_detail(match_id)
    match = detail.get("match") or {}
    can_open = bool(match.get("can_open_today")) or str(match.get("_estado_raw", "")) == "InProgress"
    if not can_open:
        messages.warning(request, "Este partido solo se puede abrir el dia programado.")
        return redirect("match_development_list")
    team_choices = match_service.team_choices_for_match(match_id)
    return render(
        request,
        "matches/match_play.html",
        {
            "detail": detail,
            "match": match,
            "match_id": match_id,
            "set_columns": display_columns(detail.get("sets") or [], "MatchSet"),
            "finish_form": FinishMatchForm(team_choices=team_choices),
            "match_play_finish_url": reverse("match_play_finish", args=[match_id]),
        },
    )


@director_required
def match_start_view(request, match_id: int):
    """Inicia partido programado para hoy."""

    if request.method == "POST":
        try:
            match_service.start_match(match_id)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("iniciar el partido"))
        else:
            log_action_safe(request, entity_name="Match", entity_id=match_id, action="start")
            messages.success(request, "Partido iniciado.")
    return redirect("match_play", match_id=match_id)


@director_required
def match_play_register_set_view(request, match_id: int):
    return _handle_match_action_to_play(request, match_id, MatchSetForm, match_service.register_match_set, "Set registrado.", "register_set")


@director_required
def match_play_point_view(request, match_id: int, side: str):
    """Registra un punto desde el tablero operativo."""

    if request.method == "POST":
        try:
            match_service.register_match_point(match_id, side)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("registrar el punto"))
        else:
            log_action_safe(request, entity_name="Match", entity_id=match_id, action=f"point_{side.upper()}")
            messages.success(request, "Punto registrado.")
    return redirect("match_play", match_id=match_id)


@director_required
def match_play_finish_view(request, match_id: int):
    return _handle_match_action_to_play(request, match_id, FinishMatchForm, match_service.finish_match, "Partido finalizado.", "finish")


@director_required
def match_status_view(request, match_id: int, status: str):
    """Cambia estado operativo desde el tablero."""

    if request.method == "POST":
        try:
            match_service.update_match_status(match_id, status)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("actualizar el estado"))
        else:
            log_action_safe(request, entity_name="Match", entity_id=match_id, action=f"status_{status}")
            messages.success(request, "Estado del partido actualizado.")
    return redirect("match_play", match_id=match_id)


@login_required
def schedule_list_view(request):
    """Vista de agenda: partidos y sesiones."""

    structure = _selected_structure_context(request)
    matches = match_service.list_schedule_matches(
        structure["selected_tournament_id"],
        structure["selected_category_id"],
        structure["selected_subcategory_id"],
    )
    sessions = match_service.list_sessions()
    match_choices = match_service.schedule_match_choices(
        structure["selected_tournament_id"],
        structure["selected_category_id"],
        structure["selected_subcategory_id"],
    )
    return render(
        request,
        "matches/schedule.html",
        {
            "matches": matches,
            "match_columns": display_columns(matches, "Match"),
            "sessions": sessions,
            "session_columns": display_columns(sessions, "Session"),
            "schedule_action_url": _filter_url(
                "schedule_match_assign",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
            ),
            "session_create_url": _filter_url(
                "session_create",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
            ),
            "session_match_add_url": _filter_url(
                "session_match_add",
                tournament_id=structure["selected_tournament_id"],
                category_id=structure["selected_category_id"],
                subcategory_id=structure["selected_subcategory_id"],
            ),
            "schedule_form": ScheduleAssignmentForm(match_choices=match_choices, court_choices=structure["court_choices"]),
            "session_form": SessionForm(),
            "session_match_form": SessionMatchForm(match_choices=match_choices),
            **structure,
        },
    )


@director_required
def schedule_match_assign_view(request):
    """Asigna fecha y cancha a un partido ya creado."""

    structure = _selected_structure_context(request)
    form = ScheduleAssignmentForm(
        request.POST or None,
        match_choices=match_service.schedule_match_choices(
            structure["selected_tournament_id"],
            structure["selected_category_id"],
            structure["selected_subcategory_id"],
        ),
        court_choices=structure["court_choices"],
    )
    if request.method == "POST" and form.is_valid():
        try:
            match_service.schedule_match_assignment(form.cleaned_data, request.session.get("user_id"))
        except Exception as exc:
            if "player_match_day_conflict" in str(exc):
                report_safe_error(request, exc, "Ese jugador ya tiene un partido asignado ese dia.")
            else:
                report_safe_error(request, exc, safe_operation_message("programar el partido"))
        else:
            log_action_safe(request, entity_name="Match", entity_id=form.cleaned_data.get("match_id"), action="schedule_from_programacion", new_value=form.cleaned_data)
            messages.success(request, "Partido programado correctamente.")
    return redirect(
        _filter_url(
            "schedule_list",
            tournament_id=structure["selected_tournament_id"],
            category_id=structure["selected_category_id"],
            subcategory_id=structure["selected_subcategory_id"],
        )
    )


@director_required
def session_create_view(request):
    """Crea sesiones/jornadas de programacion."""

    structure = _selected_structure_context(request)
    form = SessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            match_service.create_session(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear la sesion"))
        else:
            log_action_safe(request, entity_name="Session", action="create", tournament_id=form.cleaned_data.get("tournament_id"), new_value=form.cleaned_data)
            messages.success(request, "Sesion creada usando sp_create_session.")
    return redirect(
        _filter_url(
            "schedule_list",
            tournament_id=structure["selected_tournament_id"],
            category_id=structure["selected_category_id"],
            subcategory_id=structure["selected_subcategory_id"],
        )
    )


@director_required
def session_match_add_view(request):
    """Asocia partidos a sesiones existentes."""

    structure = _selected_structure_context(request)
    form = SessionMatchForm(
        request.POST or None,
        match_choices=match_service.schedule_match_choices(
            structure["selected_tournament_id"],
            structure["selected_category_id"],
            structure["selected_subcategory_id"],
        ),
    )
    if request.method == "POST" and form.is_valid():
        try:
            match_service.add_match_to_session(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("asociar el partido"))
        else:
            log_action_safe(request, entity_name="SessionMatch", action="create", entity_id=form.cleaned_data.get("session_id"), new_value=form.cleaned_data)
            messages.success(request, "Partido asociado a sesion usando sp_add_match_to_session.")
    return redirect(
        _filter_url(
            "schedule_list",
            tournament_id=structure["selected_tournament_id"],
            category_id=structure["selected_category_id"],
            subcategory_id=structure["selected_subcategory_id"],
        )
    )


