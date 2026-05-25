"""Modelos no gestionados para consultar la auditoria existente en Neon.

Trazabilidad:
`audit_service` escribe con `sp_create_audit_log` y el visor consulta esta tabla
mediante selectores seguros.
"""

from django.db import models


class AuditLog(models.Model):
    """Snapshot minimo de AuditLog; el esquema real vive en la base."""

    id = models.IntegerField(primary_key=True, db_column="id")
    action = models.CharField(max_length=120, db_column="action")
    entity_table = models.CharField(max_length=120, db_column="entity_table", blank=True, null=True)
    created_at = models.DateTimeField(db_column="created_at", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "AuditLog"
