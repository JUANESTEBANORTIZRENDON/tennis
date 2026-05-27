"""Vistas generales: landing publica y dashboard interno.

Trazabilidad:
`grand_slam_manager.urls` -> `home`/`dashboard_view` -> servicios de core ->
funciones almacenadas y selectores seguros -> templates `core/landing.html` y
`core/dashboard.html`.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.errors import report_safe_error, safe_operation_message
from apps.core.forms import AdminRowForm
from apps.core.permissions import admin_required, login_required
from apps.core.presentation import display_columns
from apps.core.services import admin_crud_service
from apps.core.services.dashboard_service import dashboard_bracket, dashboard_metrics, dashboard_tournaments, upcoming_matches
from apps.core.services.public_service import public_player_detail, public_players, public_summary, public_tournament_bracket, public_tournament_detail


def home(request):
    """Landing publica con resumen, busqueda de jugadores y detalle opcional."""

    if request.session.get("user_id"):
        return redirect("dashboard")
    query = (request.GET.get("q") or "").strip()
    selected_tournament_id = request.GET.get("tournament")
    selected_player = public_player_detail(request.GET.get("player"))
    selected_tournament = public_tournament_detail(selected_tournament_id)
    summary = public_summary()
    if not selected_tournament_id and summary.get("tournaments"):
        selected_tournament_id = summary["tournaments"][0].get("id")
    return render(
        request,
        "core/landing.html",
        {
            "query": query,
            "summary": summary,
            "players": public_players(query or None),
            "selected_player": selected_player,
            "selected_tournament": selected_tournament,
            "public_bracket": public_tournament_bracket(selected_tournament_id),
            "selected_public_tournament_id": selected_tournament_id,
        },
    )


@login_required
def dashboard_view(request):
    """Dashboard inicial para usuarios autenticados del panel."""

    selected_tournament_id = request.GET.get("tournament_id")
    try:
        selected_tournament_id = int(selected_tournament_id) if selected_tournament_id else None
    except (TypeError, ValueError):
        selected_tournament_id = None
    tournament_options, active_tournament_id = dashboard_tournaments(selected_tournament_id)
    matches = upcoming_matches()
    for match in matches:
        match_id = match.get("match_id")
        match["_actions"] = [{"label": "Abrir", "url": reverse("match_center", args=[match_id])}] if match_id else []
    return render(
        request,
        "core/dashboard.html",
        {
            "metrics": dashboard_metrics(),
            "tournament_options": tournament_options,
            "selected_tournament_id": active_tournament_id,
            "bracket": dashboard_bracket(active_tournament_id),
            "upcoming_matches": matches,
            "match_columns": ["jugador_a", "jugador_b", "fecha_partido", "lugar", "cancha", "status"],
        },
    )


@admin_required
def admin_crud_tables_view(request):
    """Entrada del administrador para CRUD de tablas del esquema."""

    rows = admin_crud_service.list_admin_tables()
    for row in rows:
        table_name = row.get("table_name")
        row["_actions"] = [{"label": "Abrir", "url": reverse("admin_crud_table", args=[table_name])}] if table_name else []
    return render(
        request,
        "core/admin_crud_list.html",
        {
            "title": "CRUD base de datos",
            "subtitle": "Administracion tecnica de tablas del sistema.",
            "rows": rows,
            "columns": display_columns(rows, "AdminTable", preferred=["table_name", "rows"]),
            "tables": rows,
        },
    )


@admin_required
def admin_crud_table_view(request, table_name: str):
    """Lista filas de una tabla y prepara acciones CRUD."""

    search = (request.GET.get("q") or "").strip()
    columns_meta = admin_crud_service.table_columns(table_name)
    pk_column = admin_crud_service.primary_key_column(columns_meta)
    rows = admin_crud_service.table_rows(table_name, search or None)
    for row in rows:
        pk_value = row.get(pk_column) if pk_column else None
        row["_actions"] = (
            [
                {"label": "Editar", "url": reverse("admin_crud_edit", args=[table_name, pk_value])},
                {"label": "Eliminar", "url": reverse("admin_crud_delete", args=[table_name, pk_value])},
            ]
            if pk_value not in (None, "")
            else []
        )
    return render(
        request,
        "core/admin_crud_list.html",
        {
            "title": f"Tabla {table_name}",
            "subtitle": "Crear, editar y eliminar registros desde procedimientos almacenados.",
            "rows": rows,
            "columns": display_columns(rows, table_name),
            "tables": admin_crud_service.list_admin_tables(),
            "selected_table": table_name,
            "primary_action_label": "Crear registro",
            "primary_action_url": reverse("admin_crud_create", args=[table_name]),
            "search": search,
        },
    )


@admin_required
def admin_crud_create_view(request, table_name: str):
    """Crea una fila desde el CRUD administrador."""

    columns_meta = admin_crud_service.table_columns(table_name)
    pk_column = admin_crud_service.primary_key_column(columns_meta)
    form = AdminRowForm(request.POST or None, columns=columns_meta, mode="create")
    if request.method == "POST" and form.is_valid():
        try:
            admin_crud_service.save_admin_row(table_name, pk_column or "id", None, form.payload())
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el registro"))
        else:
            messages.success(request, "Registro creado correctamente.")
            return redirect("admin_crud_table", table_name=table_name)
    return render(
        request,
        "core/admin_crud_form.html",
        {"title": f"Crear en {table_name}", "form": form, "back_url": reverse("admin_crud_table", args=[table_name])},
    )


@admin_required
def admin_crud_edit_view(request, table_name: str, pk_value: str):
    """Actualiza una fila desde el CRUD administrador."""

    columns_meta = admin_crud_service.table_columns(table_name)
    pk_column = admin_crud_service.primary_key_column(columns_meta)
    row = admin_crud_service.get_admin_row(table_name, pk_column or "id", pk_value)
    if not row:
        messages.warning(request, "No se encontro el registro solicitado.")
        return redirect("admin_crud_table", table_name=table_name)
    form = AdminRowForm(request.POST or None, columns=columns_meta, row=row, mode="edit")
    if request.method == "POST" and form.is_valid():
        try:
            admin_crud_service.save_admin_row(table_name, pk_column or "id", pk_value, form.payload())
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("actualizar el registro"))
        else:
            messages.success(request, "Registro actualizado correctamente.")
            return redirect("admin_crud_table", table_name=table_name)
    return render(
        request,
        "core/admin_crud_form.html",
        {"title": f"Editar {table_name}", "form": form, "back_url": reverse("admin_crud_table", args=[table_name])},
    )


@admin_required
def admin_crud_delete_view(request, table_name: str, pk_value: str):
    """Elimina una fila desde el CRUD administrador."""

    columns_meta = admin_crud_service.table_columns(table_name)
    pk_column = admin_crud_service.primary_key_column(columns_meta)
    row = admin_crud_service.get_admin_row(table_name, pk_column or "id", pk_value)
    if not row:
        messages.warning(request, "No se encontro el registro solicitado.")
        return redirect("admin_crud_table", table_name=table_name)
    if request.method == "POST":
        try:
            admin_crud_service.delete_admin_row(table_name, pk_column or "id", pk_value)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("eliminar el registro"))
        else:
            messages.success(request, "Registro eliminado correctamente.")
            return redirect("admin_crud_table", table_name=table_name)
    return render(
        request,
        "core/admin_crud_delete.html",
        {"title": f"Eliminar de {table_name}", "row": row, "back_url": reverse("admin_crud_table", args=[table_name])},
    )
