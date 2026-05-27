"""Vistas de oficiales y asignacion operativa a partidos.

Trazabilidad:
`apps.officials.urls` -> estas vistas -> `OfficialForm`/`AssignOfficialForm`
-> `official_service` -> `sp_create_official` o `sp_assign_official_to_match`
-> template `officials/official_list.html`.
"""

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.audit.services.audit_service import log_action_safe
from apps.core.errors import report_safe_error, safe_operation_message
from apps.core.permissions import director_required, login_required
from apps.core.presentation import display_columns
from apps.officials.forms import AssignOfficialForm, OfficialForm
from apps.officials.services import official_service


@login_required
def official_list_view(request):
    """Lista oficiales y muestra formularios embebidos de alta/asignacion."""

    rows = official_service.list_officials()
    return render(
        request,
        "officials/official_list.html",
        {
            "title": "Oficiales",
            "subtitle": "La licencia se enmascara para roles no autorizados.",
            "rows": rows,
            "columns": display_columns(rows, "Official"),
            "official_form": OfficialForm(),
            "assign_form": AssignOfficialForm(),
            "empty_message": "No hay oficiales registrados.",
        },
    )


@director_required
def official_create_view(request):
    """Crea un oficial mediante procedimiento almacenado."""

    form = OfficialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            official_service.create_official(form.cleaned_data)
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear el oficial"))
        else:
            log_action_safe(request, entity_name="Official", action="create", new_value=form.cleaned_data)
            messages.success(request, "Oficial creado correctamente.")
    return redirect("official_list")


@director_required
def official_assign_view(request):
    """Asigna oficial a partido con el usuario actual como responsable."""

    form = AssignOfficialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            official_service.assign_official_to_match(form.cleaned_data, request.session.get("user_id"))
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("asignar oficial"))
        else:
            log_action_safe(request, entity_name="OfficialAssignment", action="create", entity_id=form.cleaned_data.get("match_id"), new_value=form.cleaned_data)
            messages.success(request, "Oficial asignado correctamente.")
    return redirect("official_list")
