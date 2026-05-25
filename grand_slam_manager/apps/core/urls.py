"""Rutas generales del panel interno.

Estas rutas complementan la landing publica definida en `grand_slam_manager.urls`.
"""

from django.urls import path

from apps.core import views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
]
