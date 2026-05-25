"""Registro Django de la app de sanciones."""

from django.apps import AppConfig


class SanctionsConfig(AppConfig):
    """Configura `apps.sanctions` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sanctions"
