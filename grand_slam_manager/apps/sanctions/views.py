"""Vistas de sanciones, tipos de infraccion y apelaciones.

Trazabilidad:
`apps.sanctions.urls` -> estas vistas -> `SanctionForm`/`AppealForm` ->
`sanction_service` -> `sp_create_sanction` o `sp_create_sanction_appeal` ->
template `sanctions/sanction_list.html`.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.audit.services.audit_service import log_action_safe
from apps.core import form_choices
from apps.core.errors import report_safe_error, safe_operation_message
from apps.core.permissions import director_required, login_required
from apps.core.presentation import display_columns
from apps.sanctions.forms import AppealForm, SanctionForm
from apps.sanctions.services import sanction_service


@login_required
def sanction_list_view(request):
    """Pantalla combinada con listados y formularios de sancion/apelacion."""

    sanctions = sanction_service.list_sanctions()
    infraction_types = sanction_service.list_infraction_types()
    appeals = sanction_service.list_appeals()
    sanction_initial = {"match_id": request.GET.get("match_id")} if request.GET.get("match_id") else None
    return render(
        request,
        "sanctions/sanction_list.html",
        {
            "title": "Sanciones y apelaciones",
            "subtitle": "Valida que solo exista un sujeto sancionado por formulario.",
            "sanctions": sanctions,
            "sanction_columns": display_columns(sanctions, "Sanction"),
            "infraction_types": infraction_types,
            "infraction_columns": display_columns(infraction_types, "InfractionType"),
            "appeals": appeals,
            "appeal_columns": display_columns(appeals, "SanctionAppeal"),
            "sanction_form": SanctionForm(initial=sanction_initial),
            "appeal_form": AppealForm(),
            "sanction_team_player_map": form_choices.team_player_map(),
            "create_url": reverse("sanction_create"),
            "appeal_url": reverse("sanction_appeal_create"),
        },
    )


@director_required
def sanction_create_view(request):
    """Crea sancion usando el usuario actual como registrador."""

    form = SanctionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            sanction_service.create_sanction(form.cleaned_data, request.session.get("user_id"))
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear la sancion"))
        else:
            log_action_safe(request, entity_name="Sanction", action="create", new_value=form.cleaned_data)
            messages.success(request, "Sancion creada usando sp_create_sanction.")
    else:
        messages.error(request, "Formulario de sancion invalido. Revisa que solo exista un sujeto seleccionado.")
    return redirect("sanction_list")


@director_required
def sanction_appeal_create_view(request):
    """Crea apelacion vinculada a una sancion."""

    form = AppealForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            sanction_service.create_appeal(form.cleaned_data, request.session.get("user_id"))
        except Exception as exc:
            report_safe_error(request, exc, safe_operation_message("crear la apelacion"))
        else:
            log_action_safe(request, entity_name="SanctionAppeal", action="create", entity_id=form.cleaned_data.get("sanction_id"), new_value=form.cleaned_data)
            messages.success(request, "Apelacion creada usando sp_create_sanction_appeal.")
    else:
        messages.error(request, "Formulario de apelacion invalido.")
    return redirect("sanction_list")
