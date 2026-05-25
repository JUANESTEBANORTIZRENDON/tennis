"""Servicio central de auditoria.

Trazabilidad:
las vistas de negocio llaman `log_action_safe`; este servicio arma un payload
compacto y lo envia a `sp_create_audit_log`. La consulta del panel usa
`stored_select_table("AuditLog")`.

`log_action_safe` se usa en vistas para que un fallo de auditoria no bloquee la
accion principal del usuario.
"""

from __future__ import annotations

from apps.core.procedures import call_stored_procedure, stored_select_table


def list_audit_logs(filters: dict | None = None) -> list[dict]:
    """Consulta logs aplicando solo filtros presentes."""

    filters = filters or {}
    return stored_select_table(
        "AuditLog",
        filters={
            "user_id": filters.get("user_id"),
            "tournament_id": filters.get("tournament_id"),
            "entity_table": filters.get("entity_name"),
        },
        search=filters.get("q"),
        order_by_candidates=["created_at", "id"],
        limit=300,
    )


def create_audit_log(
    *,
    user_id,
    tournament_id=None,
    entity_name="",
    entity_id=None,
    entity_pk=None,
    action="",
    details=None,
    ip_address=None,
) -> None:
    """Crea un registro de auditoria con el procedimiento almacenado."""

    data = {
        "user_id": user_id,
        "tournament_id": tournament_id,
        "action": action,
        "entity_table": entity_name,
        "entity_id": entity_id,
        "entity_pk": entity_pk or (str(entity_id) if entity_id is not None else None),
        "details": details or {},
        "ip_address": ip_address,
    }
    call_stored_procedure("sp_create_audit_log", data)


def log_action_safe(request, *, entity_name: str, action: str, entity_id=None, tournament_id=None, new_value=None) -> None:
    """Registra auditoria como esfuerzo mejor: nunca rompe el flujo principal."""

    try:
        create_audit_log(
            user_id=request.session.get("user_id"),
            tournament_id=tournament_id,
            entity_name=entity_name,
            entity_id=entity_id if isinstance(entity_id, int) else None,
            entity_pk=str(entity_id) if entity_id is not None else None,
            action=action,
            details={"new_value": new_value} if new_value is not None else {},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
    except Exception:
        # Audit logging must never break the main administrative action.
        pass
