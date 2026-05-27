"""Rutas generales del panel interno.

Estas rutas complementan la landing publica definida en `grand_slam_manager.urls`.
"""

from django.urls import path

from apps.core import views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("admin-data/", views.admin_crud_tables_view, name="admin_crud_tables"),
    path("admin-data/<str:table_name>/", views.admin_crud_table_view, name="admin_crud_table"),
    path("admin-data/<str:table_name>/create/", views.admin_crud_create_view, name="admin_crud_create"),
    path("admin-data/<str:table_name>/<str:pk_value>/edit/", views.admin_crud_edit_view, name="admin_crud_edit"),
    path("admin-data/<str:table_name>/<str:pk_value>/delete/", views.admin_crud_delete_view, name="admin_crud_delete"),
]
