"""Vistas de torneos, canchas y estructura Category/SubCategory/Round.

Trazabilidad:
`apps.tournaments.urls` -> estas vistas -> formularios del modulo ->
`tournament_service` -> funciones/procedimientos `sp_*` en Neon -> templates
`tournaments/*` y `shared/*`.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.audit.services.audit_service import log_action_safe
from apps.core.db import get_value, row_identifier
from apps.core.errors import report_safe_error, safe_operation_message
from apps.core.permissions import director_required, login_required
from apps.core.presentation import display_columns
from apps.tournaments.forms import CategoryForm, CourtForm, RoundForm, SubCategoryForm, TournamentForm
from apps.tournaments.services import tournament_service


def _initial_from_row(row: dict | None, fields: list[str]) -> dict:
    """Extrae datos existentes para formularios de edicion."""

    return {field: get_value(row, field) for field in fields if get_value(row, field) is not None}


def _selected_tournament_id(request) -> int | None:
    value = request.GET.get("tournament_id") or request.POST.get("tournament_id")
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _category_url(tournament_id: int | None) -> str:
    base_url = reverse("category_tree")
    return f"{base_url}?tournament_id={tournament_id}" if tournament_id else base_url


def _render_category_tree(request, *, category_form=None, subcategory_form=None, round_form=None):
    """Renderiza la pagina combinada de categorias conservando errores."""

    selected_tournament_id = _selected_tournament_id(request)
    tree = tournament_service.category_tree_for_tournament(selected_tournament_id)
    selected_tournament_id = tree.get("selected_tournament_id")
    category_choices = tournament_service.choice_rows(tree["categories"], label_keys=("name", "mode", "gender"))
    subcategory_choices = tournament_service.choice_rows(tree["subcategories"], label_keys=("name", "categoria"))
    tournament_options = [
        {
            "id": get_value(row, "id", "tournament_id"),
            "label": f"{get_value(row, 'name', default='Torneo')} {get_value(row, 'year', default='')}".strip(),
            "selected": str(get_value(row, "id", "tournament_id")) == str(selected_tournament_id),
        }
        for row in tree["tournaments"]
    ]
    return render(
        request,
        "tournaments/category_tree.html",
        {
            "tree": tree,
            "selected_tournament_id": selected_tournament_id,
            "selected_category_url": _category_url(selected_tournament_id),
            "category_create_url": f"{reverse('category_create')}?tournament_id={selected_tournament_id}" if selected_tournament_id else reverse("category_create"),
            "subcategory_create_url": f"{reverse('subcategory_create')}?tournament_id={selected_tournament_id}" if selected_tournament_id else reverse("subcategory_create"),
            "round_create_url": f"{reverse('round_create')}?tournament_id={selected_tournament_id}" if selected_tournament_id else reverse("round_create"),
            "round_generate_url": reverse("round_generate"),
            "tournament_options": tournament_options,
            "category_form": category_form or CategoryForm(tournament_id=selected_tournament_id),
            "subcategory_form": subcategory_form or SubCategoryForm(category_choices=category_choices),
            "round_form": round_form or RoundForm(subcategory_choices=subcategory_choices),
            "category_columns": tournament_service.category_columns(tree["categories"], "Category"),
            "subcategory_columns": tournament_service.category_columns(tree["subcategories"], "SubCategory"),
            "round_columns": tournament_service.category_columns(tree["rounds"], "Round"),
        },
    )


def _add_round_database_error(form, exc: Exception) -> None:
    """Traduce restricciones SQL conocidas a errores de formulario legibles."""

    message = str(exc)
    if "chk_round_best_of_sets" in message:
        form.add_error("best_of_sets", "Selecciona 1, 3 o 5 sets.")
    elif "uq_round_business" in message:
        form.add_error("round_number", "Ya existe una ronda con ese numero para el cuadro seleccionado.")
    else:
        form.add_error(None, "No se pudo crear la ronda. Revisa los datos e intentalo nuevamente.")


def _round_generation_message(exc: Exception) -> str:
    message = str(exc)
    if "draw_not_full" in message or "tournament_entries_incomplete" in message:
        return "Antes de generar rondas debes completar todas las inscripciones del cuadro."
    if "invalid_grand_slam_draw_size" in message:
        return "El tamano del cuadro debe ser 2, 4, 8, 16, 32, 64 o 128."
    return safe_operation_message("generar las rondas")


@login_required
def tournament_list_view(request):
    """Lista torneos y agrega acciones de edicion por fila."""

    rows = tournament_service.list_tournaments()
    columns = display_columns(rows, "Tournament")
    for row in rows:
        pk = row_identifier(row, "tournament_id")
        row["_actions"] = [
            {"label": "Ver", "url": reverse("tournament_detail", args=[pk])},
            {"label": "Editar", "url": reverse("tournament_edit", args=[pk])},
        ] if pk else []
    return render(
        request,
        "shared/entity_list.html",
        {
            "title": "Torneos",
            "subtitle": "Administracion de torneos cargados desde Neon.",
            "rows": rows,
            "columns": columns,
            "primary_action_label": "Crear torneo",
            "primary_action_url": reverse("tournament_create"),
            "empty_message": "No hay torneos registrados.",
        },
    )


@login_required
def tournament_detail_view(request, tournament_id: int):
    """Detalle de torneo con categorias y tamanos de cuadros."""

    detail = tournament_service.tournament_detail(tournament_id)
    tournament = detail["tournament"]
    if not tournament:
        messages.warning(request, "No se encontro el torneo solicitado.")
        return redirect("tournament_list")
    return render(
        request,
        "tournaments/tournament_detail.html",
        {
            "title": get_value(tournament, "name", default="Torneo"),
            "tournament": tournament,
            "tournament_rows": [tournament],
            "tournament_columns": display_columns([tournament], "Tournament"),
            "categories": detail["categories"],
            "category_columns": display_columns(detail["categories"], "Category"),
            "subcategories": detail["subcategories"],
            "subcategory_columns": display_columns(detail["subcategories"], "SubCategory"),
            "rounds": detail["rounds"],
            "round_columns": display_columns(detail["rounds"], "Round"),
        },
    )


@director_required
def tournament_create_view(request):
    """Crea torneos mediante sp_create_tournament."""

    form = TournamentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            tournament_service.create_tournament(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el torneo"))
        else:
            log_action_safe(request, entity_name="Tournament", action="create", new_value=form.cleaned_data)
            messages.success(request, "Torneo creado usando sp_create_tournament.")
            return redirect("tournament_list")
    return render(request, "shared/form_page.html", {"title": "Crear torneo", "form": form, "back_url": reverse("tournament_list")})


@director_required
def tournament_edit_view(request, tournament_id: int):
    """Edita torneos existentes mediante sp_update_tournament."""

    row = tournament_service.get_tournament(tournament_id)
    initial = _initial_from_row(row, ["name", "year", "start_date", "end_date", "location", "surface", "status", "description"])
    form = TournamentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            tournament_service.update_tournament(tournament_id, form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("actualizar el torneo"))
        else:
            log_action_safe(request, entity_name="Tournament", entity_id=tournament_id, action="update", new_value=form.cleaned_data)
            messages.success(request, "Torneo actualizado usando sp_update_tournament.")
            return redirect("tournament_list")
    return render(request, "shared/form_page.html", {"title": "Editar torneo", "form": form, "back_url": reverse("tournament_list")})


@login_required
def court_list_view(request):
    """Lista canchas y muestra si su superficie coincide con el torneo."""

    rows = tournament_service.list_courts()
    return render(
        request,
        "tournaments/court_list.html",
        {
            "title": "Canchas",
            "subtitle": "La columna surface_matches ayuda a validar que la superficie de la cancha coincida con el torneo.",
            "rows": rows,
            "columns": display_columns(rows, "Court"),
            "primary_action_label": "Crear cancha",
            "primary_action_url": reverse("court_create"),
            "empty_message": "No hay canchas registradas.",
        },
    )


@director_required
def court_create_view(request):
    """Crea canchas mediante sp_create_court."""

    form = CourtForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            tournament_service.create_court(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear la cancha"))
        else:
            log_action_safe(request, entity_name="Court", action="create", tournament_id=form.cleaned_data.get("tournament_id"), new_value=form.cleaned_data)
            messages.success(request, "Cancha creada usando sp_create_court.")
            return redirect("court_list")
    return render(request, "shared/form_page.html", {"title": "Crear cancha", "form": form, "back_url": reverse("court_list")})


@login_required
def category_tree_view(request):
    """Muestra la jerarquia completa de competencia."""

    return _render_category_tree(request)


@director_required
def category_create_view(request):
    """Crea una categoria y vuelve al arbol competitivo."""

    selected_tournament_id = _selected_tournament_id(request)
    form = CategoryForm(request.POST or None, tournament_id=selected_tournament_id)
    if request.method == "POST" and form.is_valid():
        try:
            tournament_service.create_category(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear la categoria"))
        else:
            log_action_safe(request, entity_name="Category", action="create", tournament_id=form.cleaned_data.get("tournament_id"), new_value=form.cleaned_data)
            messages.success(request, "Categoria creada usando sp_create_category.")
    elif request.method == "POST":
        messages.error(request, "Revisa los campos de la categoria antes de crearla.")
        return _render_category_tree(request, category_form=form)
    return redirect(_category_url(form.cleaned_data.get("tournament_id") if form.is_valid() else selected_tournament_id))


@director_required
def subcategory_create_view(request):
    """Crea un cuadro competitivo dentro de una categoria."""

    selected_tournament_id = _selected_tournament_id(request)
    tree = tournament_service.category_tree_for_tournament(selected_tournament_id)
    category_choices = tournament_service.choice_rows(tree["categories"], label_keys=("name", "mode", "gender"))
    form = SubCategoryForm(request.POST or None, category_choices=category_choices)
    if request.method == "POST" and form.is_valid():
        try:
            tournament_service.create_subcategory(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el cuadro"))
        else:
            log_action_safe(request, entity_name="SubCategory", action="create", new_value=form.cleaned_data)
            messages.success(request, "Cuadro creado usando sp_create_subcategory.")
    elif request.method == "POST":
        messages.error(request, "Revisa los campos del cuadro antes de crearlo.")
        return _render_category_tree(request, subcategory_form=form)
    return redirect(_category_url(tree.get("selected_tournament_id")))


@director_required
def round_create_view(request):
    """Crea una ronda validando errores de formulario y restricciones SQL."""

    selected_tournament_id = _selected_tournament_id(request)
    tree = tournament_service.category_tree_for_tournament(selected_tournament_id)
    subcategory_choices = tournament_service.choice_rows(tree["subcategories"], label_keys=("name", "categoria"))
    form = RoundForm(request.POST or None, subcategory_choices=subcategory_choices)
    if request.method == "POST" and form.is_valid():
        try:
            tournament_service.create_round(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc)
            _add_round_database_error(form, exc)
            return _render_category_tree(request, round_form=form)
        else:
            log_action_safe(request, entity_name="Round", action="create", new_value=form.cleaned_data)
            messages.success(request, "Ronda creada usando sp_create_round.")
    elif request.method == "POST":
        messages.error(request, "Revisa los campos de la ronda antes de crearla.")
        return _render_category_tree(request, round_form=form)
    return redirect(_category_url(tree.get("selected_tournament_id")))


@director_required
def round_generate_view(request):
    """Genera rondas para los cuadros completos del torneo seleccionado."""

    tournament_id = _selected_tournament_id(request)
    if request.method == "POST" and tournament_id:
        try:
            tournament_service.generate_rounds_for_tournament(tournament_id)
        except Exception as exc:
            report_safe_error(request, exc, _round_generation_message(exc))
        else:
            log_action_safe(request, entity_name="Tournament", entity_id=tournament_id, action="generate_rounds")
            messages.success(request, "Rondas generadas segun el tamano de cada cuadro.")
    return redirect(_category_url(tournament_id))
