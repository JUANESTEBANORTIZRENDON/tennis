"""Registro Django de la app de torneos."""

from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    """Configura `apps.tournaments` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tournaments"
