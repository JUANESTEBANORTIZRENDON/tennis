"""Rutas de autenticacion y administracion de usuarios.

Cada nombre de ruta se usa en `reverse()` desde vistas/templates para mantener
trazabilidad entre navegacion, accion y vista que procesa el request.
"""

from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/verify/", views.login_verify_view, name="login_verify"),
    path("logout/", views.logout_view, name="logout"),
    path("users/", views.user_list_view, name="user_list"),
    path("users/create/", views.user_create_view, name="user_create"),
    path("users/<int:user_id>/password/", views.user_password_change_view, name="user_password_change"),
]
