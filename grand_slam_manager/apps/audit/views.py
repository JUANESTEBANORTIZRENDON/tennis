"""Pantallas de consulta de auditoria para administradores y auditores.

Trazabilidad:
`apps.audit.urls` -> `audit_list_view` -> `AuditFilterForm` ->
`audit_service.list_audit_logs` -> tabla/funcion segura de AuditLog ->
template `audit/audit_list.html`.
"""

from django.shortcuts import render

from apps.audit.forms import AuditFilterForm
from apps.audit.services.audit_service import list_audit_logs
from apps.core.permissions import AUDITOR, ADMIN_ROLES, roles_required
from apps.core.presentation import display_columns


@roles_required(*(ADMIN_ROLES | {AUDITOR}))
def audit_list_view(request):
    """Renderiza AuditLog con filtros seguros y columnas detectadas."""

    form = AuditFilterForm(request.GET or None)
    filters = form.cleaned_data if form.is_valid() else {}
    rows = list_audit_logs(filters)
    return render(
        request,
        "audit/audit_list.html",
        {
            "title": "Auditoria",
            "subtitle": "Trazabilidad de acciones criticas.",
            "rows": rows,
            "columns": display_columns(rows, "AuditLog"),
            "filter_form": form,
            "empty_message": "No hay registros de auditoria para los filtros actuales.",
            "show_create": False,
        },
    )
