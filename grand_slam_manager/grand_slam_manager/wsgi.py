"""Punto de entrada WSGI para despliegues tradicionales."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grand_slam_manager.settings")

application = get_wsgi_application()
