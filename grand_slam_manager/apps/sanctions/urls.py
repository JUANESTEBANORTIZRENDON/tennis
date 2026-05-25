"""Rutas de sanciones y apelaciones.

El listado renderiza formularios embebidos; los POST separados llaman
`sanction_service`.
"""

from django.urls import path

from apps.sanctions import views

urlpatterns = [
    path("sanctions/", views.sanction_list_view, name="sanction_list"),
    path("sanctions/create/", views.sanction_create_view, name="sanction_create"),
    path("sanctions/appeals/create/", views.sanction_appeal_create_view, name="sanction_appeal_create"),
]
