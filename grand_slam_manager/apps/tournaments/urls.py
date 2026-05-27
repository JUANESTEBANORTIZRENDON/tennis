"""Rutas de torneos, canchas y estructura competitiva.

El nombre de cada ruta conecta botones/forms con la vista que llama a
`tournament_service` y sus procedimientos almacenados.
"""

from django.urls import path

from apps.tournaments import views

urlpatterns = [
    path("tournaments/", views.tournament_list_view, name="tournament_list"),
    path("tournaments/create/", views.tournament_create_view, name="tournament_create"),
    path("tournaments/<int:tournament_id>/", views.tournament_detail_view, name="tournament_detail"),
    path("tournaments/<int:tournament_id>/edit/", views.tournament_edit_view, name="tournament_edit"),
    path("courts/", views.court_list_view, name="court_list"),
    path("courts/create/", views.court_create_view, name="court_create"),
    path("categories/", views.category_tree_view, name="category_tree"),
    path("categories/create/", views.category_create_view, name="category_create"),
    path("subcategories/create/", views.subcategory_create_view, name="subcategory_create"),
]
