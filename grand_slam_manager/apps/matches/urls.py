"""Rutas de partidos, match center y programacion.

Las rutas separan lectura, match center y tablero de juego; cada POST termina
en una vista que llama un procedimiento de `match_service`.
"""

from django.urls import path

from apps.matches import views

urlpatterns = [
    path("matches/", views.match_list_view, name="match_list"),
    path("matches/create/", views.match_create_view, name="match_create"),
    path("matches/generate-first-round/", views.match_generate_first_round_view, name="match_generate_first_round"),
    path("matches/development/", views.match_development_list_view, name="match_development_list"),
    path("matches/<int:match_id>/center/", views.match_center_view, name="match_center"),
    path("matches/<int:match_id>/play/", views.match_play_view, name="match_play"),
    path("matches/<int:match_id>/play/start/", views.match_start_view, name="match_start"),
    path("matches/<int:match_id>/play/point/<str:side>/", views.match_play_point_view, name="match_play_point"),
    path("matches/<int:match_id>/play/sets/register/", views.match_play_register_set_view, name="match_play_register_set"),
    path("matches/<int:match_id>/play/finish/", views.match_play_finish_view, name="match_play_finish"),
    path("matches/<int:match_id>/play/status/<str:status>/", views.match_status_view, name="match_status"),
    path("matches/<int:match_id>/participants/add/", views.match_add_participant_view, name="match_add_participant"),
    path("matches/<int:match_id>/sets/register/", views.match_register_set_view, name="match_register_set"),
    path("matches/<int:match_id>/finish/", views.match_finish_view, name="match_finish"),
    path("matches/<int:match_id>/schedule/", views.match_schedule_view, name="match_schedule"),
    path("matches/<int:match_id>/reschedule/", views.match_reschedule_view, name="match_reschedule"),
    path("schedule/", views.schedule_list_view, name="schedule_list"),
    path("schedule/sessions/create/", views.session_create_view, name="session_create"),
    path("schedule/sessions/matches/add/", views.session_match_add_view, name="session_match_add"),
]
