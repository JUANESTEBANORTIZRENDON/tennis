"""Registro Django de la app de partidos."""

from django.apps import AppConfig


class MatchesConfig(AppConfig):
    """Configura `apps.matches` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.matches"
