"""Configuracion principal de Victory's.

Carga variables desde `.env`, conecta Django con Neon/PostgreSQL, activa
Whitenoise para estaticos y usa sesiones firmadas en cookies para el panel.
"""

from pathlib import Path
import os
from urllib.parse import parse_qs, urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Variables obligatorias: sin clave secreta ni DATABASE_URL el proyecto no debe
# arrancar, porque las sesiones y la conexion a Neon dependen de ellas.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be configured in .env")

DEBUG = os.getenv("DEBUG", "False").strip().lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.accounts",
    "apps.tournaments",
    "apps.players",
    "apps.matches",
    "apps.officials",
    "apps.sanctions",
    "apps.audit",
]

# El proyecto evita dependencias pesadas de autenticacion y administra sesiones
# propias; por eso solo instala los componentes Django necesarios.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "grand_slam_manager.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.navigation_context",
            ],
        },
    }
]

WSGI_APPLICATION = "grand_slam_manager.wsgi.application"
ASGI_APPLICATION = "grand_slam_manager.asgi.application"

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must be configured in .env")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    )
}
DATABASES["default"].setdefault("OPTIONS", {})
# Neon expone opciones como sslmode/channel_binding en la URL. Se copian a
# OPTIONS para que psycopg respete exactamente la cadena de conexion.
_db_query = parse_qs(urlparse(DATABASE_URL).query)
for _option in ("sslmode", "channel_binding"):
    if _option in _db_query:
        DATABASES["default"]["OPTIONS"][_option] = _db_query[_option][0]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
# Las sesiones firmadas evitan tabla de sesiones, pero vuelven importante
# proteger SECRET_KEY y servir cookies seguras fuera de DEBUG.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
LOGIN_URL = "/login/"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
# Configuracion de correo usada por el flujo opcional de doble factor.
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "webmaster@localhost")
EMAIL_2FA_ENABLED = os.getenv("EMAIL_2FA_ENABLED", "True").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_2FA_TIMEOUT_MINUTES = int(os.getenv("EMAIL_2FA_TIMEOUT_MINUTES", "10"))

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

