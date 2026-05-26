"""Rutas de jugadores, lesiones, equipos e inscripciones.

Los nombres de ruta enlazan acciones de templates con vistas que delegan en
`player_service`.
"""

from django.urls import path

from apps.players import views

urlpatterns = [
    path("players/", views.player_list_view, name="player_list"),
    path("players/create/", views.player_create_view, name="player_create"),
    path("players/<str:player_id>/", views.player_detail_view, name="player_detail"),
    path("injuries/", views.injury_list_view, name="injury_list"),
    path("injuries/register/", views.injury_register_view, name="injury_register"),
    path("injuries/close/", views.injury_close_view, name="injury_close"),
    path("teams/", views.team_list_view, name="team_list"),
    path("teams/create/", views.team_create_view, name="team_create"),
    path("teams/members/add/", views.team_member_add_view, name="team_member_add"),
    path("coaches/", views.coach_list_view, name="coach_list"),
    path("coaches/create/", views.coach_create_view, name="coach_create"),
    path("coaches/players/add/", views.coach_player_add_view, name="coach_player_add"),
    path("entries/", views.entry_list_view, name="entry_list"),
    path("entries/create/", views.entry_create_view, name="entry_create"),
    path("entries/players/add/", views.entry_player_create_view, name="entry_player_create"),
]
