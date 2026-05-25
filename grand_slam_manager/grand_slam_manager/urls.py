"""Rutas raiz de Victory's.

Cada app registra sus propias URL bajo la raiz para mantener enlaces simples
(`/players/`, `/matches/`, etc.). La landing publica vive en `/`.

Trazabilidad general:
URL raiz -> vista de cada app -> formulario/servicio -> Neon/PostgreSQL ->
template. Las apps mantienen sus rutas locales en `apps.<modulo>.urls`.
"""

from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from apps.core.views import home

urlpatterns = [
    path("", home, name="home"),
    # Cada include expone rutas de un dominio funcional y conserva nombres
    # estables para `reverse()` en vistas, formularios y templates.
    path("", include("apps.accounts.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.tournaments.urls")),
    path("", include("apps.players.urls")),
    path("", include("apps.matches.urls")),
    path("", include("apps.officials.urls")),
    path("", include("apps.sanctions.urls")),
    path("", include("apps.audit.urls")),
]

handler400 = "apps.core.errors.bad_request_view"
handler403 = "apps.core.errors.permission_denied_view"
handler404 = "apps.core.errors.page_not_found_view"
handler500 = "apps.core.errors.server_error_view"

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
