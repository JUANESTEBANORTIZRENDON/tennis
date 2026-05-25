"""Registro Django de la app de jugadores."""

from django.apps import AppConfig


class PlayersConfig(AppConfig):
    """Configura `apps.players` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.players"
