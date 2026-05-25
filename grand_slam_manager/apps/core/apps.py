"""Registro Django de utilidades centrales."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configura `apps.core` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
