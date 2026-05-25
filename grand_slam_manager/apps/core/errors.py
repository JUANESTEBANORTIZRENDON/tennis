"""Mensajes de error seguros para respuestas visibles al usuario."""

from __future__ import annotations

import logging
from typing import Final

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render

SAFE_DATABASE_ERROR: Final = "No se pudo completar la operacion. Revisa los datos e intentalo nuevamente."
SAFE_SYSTEM_ERROR: Final = "Ocurrio un error inesperado. Intentalo nuevamente mas tarde."
SAFE_EMAIL_ERROR: Final = "No se pudo enviar el codigo de verificacion. Intentalo nuevamente mas tarde."

logger = logging.getLogger(__name__)


def safe_operation_message(action: str) -> str:
    return f"No se pudo {action}. Revisa los datos e intentalo nuevamente."


def report_safe_error(request: HttpRequest, exc: Exception, message: str | None = None) -> None:
    """Registra el detalle tecnico y muestra un mensaje preconfigurado."""

    logger.exception("Operacion rechazada por una excepcion controlada.")
    if message:
        public_message = message
    elif isinstance(exc, (DatabaseError, IntegrityError)):
        public_message = SAFE_DATABASE_ERROR
    else:
        public_message = SAFE_SYSTEM_ERROR
    messages.error(request, public_message)


def bad_request_view(request: HttpRequest, exception: Exception) -> HttpResponseBadRequest:
    return render(request, "errors/400.html", status=400)


def permission_denied_view(request: HttpRequest, exception: Exception) -> HttpResponseForbidden:
    return render(request, "errors/403.html", status=403)


def page_not_found_view(request: HttpRequest, exception: Exception) -> HttpResponseNotFound:
    return render(request, "errors/404.html", status=404)


def server_error_view(request: HttpRequest) -> HttpResponse:
    return render(request, "errors/500.html", status=500)
