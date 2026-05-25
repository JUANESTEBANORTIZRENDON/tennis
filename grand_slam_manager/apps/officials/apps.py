"""Registro Django de la app de oficiales."""

from django.apps import AppConfig


class OfficialsConfig(AppConfig):
    """Configura `apps.officials` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.officials"
