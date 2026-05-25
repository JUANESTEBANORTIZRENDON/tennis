"""Ruta del visor de auditoria.

Apunta al listado filtrable de `AuditLog` usado por roles de control.
"""

from django.urls import path

from apps.audit import views

urlpatterns = [
    path("audit/", views.audit_list_view, name="audit_list"),
]
