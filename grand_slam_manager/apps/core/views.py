"""Vistas generales: landing publica y dashboard interno.

Trazabilidad:
`grand_slam_manager.urls` -> `home`/`dashboard_view` -> servicios de core ->
funciones almacenadas y selectores seguros -> templates `core/landing.html` y
`core/dashboard.html`.
"""

from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.permissions import login_required
from apps.core.services.dashboard_service import dashboard_bracket, dashboard_metrics, dashboard_tournaments, upcoming_matches
from apps.core.services.public_service import public_player_detail, public_players, public_summary, public_tournament_bracket, public_tournament_detail


def home(request):
    """Landing publica con resumen, busqueda de jugadores y detalle opcional."""

    if request.session.get("user_id"):
        return redirect("dashboard")
    query = (request.GET.get("q") or "").strip()
    selected_tournament_id = request.GET.get("tournament")
    selected_player = public_player_detail(request.GET.get("player"))
    selected_tournament = public_tournament_detail(selected_tournament_id)
    summary = public_summary()
    if not selected_tournament_id and summary.get("tournaments"):
        selected_tournament_id = summary["tournaments"][0].get("id")
    return render(
        request,
        "core/landing.html",
        {
            "query": query,
            "summary": summary,
            "players": public_players(query or None),
            "selected_player": selected_player,
            "selected_tournament": selected_tournament,
            "public_bracket": public_tournament_bracket(selected_tournament_id),
            "selected_public_tournament_id": selected_tournament_id,
        },
    )


@login_required
def dashboard_view(request):
    """Dashboard inicial para usuarios autenticados del panel."""

    selected_tournament_id = request.GET.get("tournament_id")
    try:
        selected_tournament_id = int(selected_tournament_id) if selected_tournament_id else None
    except (TypeError, ValueError):
        selected_tournament_id = None
    tournament_options, active_tournament_id = dashboard_tournaments(selected_tournament_id)
    matches = upcoming_matches()
    for match in matches:
        match_id = match.get("match_id")
        match["_actions"] = [{"label": "Abrir", "url": reverse("match_center", args=[match_id])}] if match_id else []
    return render(
        request,
        "core/dashboard.html",
        {
            "metrics": dashboard_metrics(),
            "tournament_options": tournament_options,
            "selected_tournament_id": active_tournament_id,
            "bracket": dashboard_bracket(active_tournament_id),
            "upcoming_matches": matches,
            "match_columns": ["jugador_a", "jugador_b", "fecha_partido", "lugar", "cancha", "status"],
        },
    )
