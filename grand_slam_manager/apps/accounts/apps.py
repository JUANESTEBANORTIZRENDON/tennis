"""Registro Django de la app de cuentas."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configura `apps.accounts` dentro de INSTALLED_APPS."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
