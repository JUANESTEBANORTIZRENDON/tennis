"""Contexto global para navegacion, usuario actual y permisos de UI.

Trazabilidad:
`settings.TEMPLATES.context_processors` carga este modulo en cada request;
`base.html` consume `nav_items`, `current_user`, `can_write` y banderas de rol.
"""

from __future__ import annotations

from django.urls import reverse

from apps.core.permissions import can_view_sensitive, can_write, current_user, is_admin_role, is_director_role


NAV_ITEMS = [
    ("dashboard", "Resumen", "dashboard", "Resumen", "all"),
    ("entries", "Inscripciones", "entry_list", "Operacion", "director"),
    ("matches", "Match Center", "match_list", "Operacion", "all"),
    ("match_development", "Desarrollo partido", "match_development_list", "Operacion", "director"),
    ("schedule", "Programacion", "schedule_list", "Operacion", "director"),
    ("tournaments", "Torneo", "tournament_list", "Competencia", "all"),
    ("categories", "Categorias", "category_tree", "Competencia", "director"),
    ("courts", "Canchas", "court_list", "Competencia", "director"),
    ("teams", "Equipos", "team_list", "Participantes", "director"),
    ("players", "Jugadores", "player_list", "Participantes", "all"),
    ("coaches", "Entrenadores", "coach_list", "Participantes", "director"),
    ("officials", "Oficiales", "official_list", "Participantes", "director"),
    ("sanctions", "Sanciones", "sanction_list", "Informacion", "all"),
    ("injuries", "Lesiones", "injury_list", "Informacion", "director"),
    ("users", "Usuarios", "user_list", "Sistema", "admin"),
    ("audit", "Auditoria", "audit_list", "Sistema", "admin"),
]


def navigation_context(request):
    """Construye el menu lateral segun rol y expone banderas de plantilla.

    Las URLs salen de los nombres registrados en cada `apps.<modulo>.urls`.
    """

    role_is_admin = is_admin_role(request)
    role_is_director = is_director_role(request)
    current_path = request.path
    nav_items = []
    for key, label, url_name, group, audience in NAV_ITEMS:
        if audience == "admin" and not role_is_admin:
            continue
        if audience == "director" and role_is_admin and not role_is_director:
            continue
        try:
            url = reverse(url_name)
        except Exception:
            url = "#"
        nav_items.append({"key": key, "label": label, "url": url, "url_name": url_name, "group": group, "is_active": False})
    matching_items = [
        item
        for item in nav_items
        if item["url"] != "#" and (current_path == item["url"] or current_path.startswith(item["url"]))
    ]
    if matching_items:
        best_match = max(matching_items, key=lambda item: len(item["url"]))
        best_match["is_active"] = True
    panel_variant = "admin" if role_is_admin else "director" if role_is_director else "guest"
    return {
        "nav_items": nav_items,
        "current_user": current_user(request),
        "can_write": can_write(request),
        "can_view_sensitive": can_view_sensitive(request),
        "is_admin_panel": role_is_admin,
        "is_director_panel": role_is_director,
        "panel_variant": panel_variant,
    }
