"""Registro Django de la app de auditoria."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configura `apps.audit` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
