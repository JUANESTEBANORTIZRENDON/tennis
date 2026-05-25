"""Rutas de oficiales y asignaciones.

Conectan el listado con altas/asignaciones que se resuelven en
`official_service`.
"""

from django.urls import path

from apps.officials import views

urlpatterns = [
    path("officials/", views.official_list_view, name="official_list"),
    path("officials/create/", views.official_create_view, name="official_create"),
    path("officials/assign/", views.official_assign_view, name="official_assign"),
]
