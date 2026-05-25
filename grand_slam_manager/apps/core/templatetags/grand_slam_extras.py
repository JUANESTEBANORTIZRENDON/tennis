"""Filtros de plantilla para mostrar datos sensibles y valores genericos."""

from django import template

register = template.Library()

SENSITIVE_TOKENS = ("document", "passport", "license", "licencia", "identification", "player_id")
STATUS_TOKENS = ("status", "state", "estado", "surface_matches", "active")
DISPLAY_LABELS = {
    "action": "Accion",
    "active": "Activo",
    "available_slots": "Cupos disponibles",
    "assigned_at": "Asignada",
    "birth_date": "Fecha de nacimiento",
    "capacity": "Capacidad",
    "category": "Categoría",
    "certification_level": "Certificacion",
    "categoria": "Categoría",
    "country_code": "País",
    "cuadro": "Cuadro",
    "codigo_partido": "Codigo partido",
    "currency": "Moneda",
    "default_sanction_type": "Sanción sugerida",
    "description": "Descripcion",
    "draw_size": "Tamaño del cuadro",
    "equipo": "Equipo",
    "estado": "Estado",
    "email": "Correo",
    "end_date": "Fin",
    "end_datetime": "Fin",
    "entity_pk": "Registro",
    "entity_table": "Entidad",
    "fine_amount": "Multa",
    "fecha_partido": "Fecha del partido",
    "first_name": "Nombre",
    "filed_at": "Fecha de apelacion",
    "filed_by_player_id": "Apelado por",
    "full_name": "Nombre",
    "games_won": "Games",
    "gender": "Genero",
    "hand": "Mano",
    "indoor": "Cubierta",
    "injury_date": "Fecha lesión",
    "injury_type_id": "Tipo de lesión",
    "tipo_lesion": "Tipo de lesión",
    "ip_address": "IP",
    "is_active": "Activo",
    "is_winner": "Ganador",
    "issued_at": "Fecha sanción",
    "last_name": "Apellido",
    "license_number": "Licencia",
    "location": "Lugar",
    "name": "Nombre",
    "nationality": "Nacionalidad",
    "notes": "Notas",
    "official_id": "Oficial",
    "official_type": "Tipo de oficial",
    "penalty_games": "Games de sanción",
    "penalty_points": "Puntos de sanción",
    "phone": "Telefono",
    "player_id": "Jugador",
    "player_name": "Jugador",
    "points_won": "Puntos",
    "qualifying_method": "Clasificacion",
    "ranking_at_entry": "Ranking",
    "recovery_date": "Recuperacion",
    "ronda": "Ronda",
    "scheduled_datetime": "Fecha del partido",
    "seed": "Siembra",
    "set_number": "Set",
    "sets_won": "Sets",
    "side": "Lado",
    "start_date": "Inicio",
    "start_datetime": "Inicio",
    "status": "Estado",
    "surface": "Superficie",
    "surface_matches": "Superficie valida",
    "team_a_games": "Games equipo A",
    "team_b_games": "Games equipo B",
    "team_id": "Equipo",
    "tie_break_a": "Tie break A",
    "tie_break_b": "Tie break B",
    "tournament_surface": "Superficie del torneo",
    "torneo": "Torneo",
    "turned_pro_year": "Profesional desde",
    "user_id": "Usuario",
    "violation_type_id": "Infraccion",
    "winner_team_id": "Ganador",
    "winning_team_id": "Ganador",
    "year": "Año",
}


@register.filter
def get_item(mapping, key):
    """Permite acceder a diccionarios con una llave dinamica en templates."""

    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def humanize_key(value):
    """Convierte nombres de columna tecnicos en etiquetas legibles."""

    key = str(value)
    return DISPLAY_LABELS.get(key.lower(), key.replace("_", " ").title())


@register.filter
def is_status_column(value):
    """Detecta columnas que deben renderizarse como badges."""

    lowered = str(value).lower()
    return any(token in lowered for token in STATUS_TOKENS)


@register.simple_tag
def render_cell(value, column_name="", can_view_sensitive=False, mask_plain_id=False):
    """Formatea celdas y enmascara datos sensibles segun permisos."""

    if value is None or value == "":
        return "-"
    column = str(column_name).lower()
    should_mask_plain_id = mask_plain_id and column == "id"
    if not can_view_sensitive and (should_mask_plain_id or any(token in column for token in SENSITIVE_TOKENS)):
        text = str(value)
        tail = text[-4:] if len(text) >= 4 else text
        return "****" + tail
    if isinstance(value, bool):
        return "Si" if value else "No"
    return str(value)


@register.filter
def badge_class(value):
    """Devuelve la clase visual para estados positivos, neutros o alerta."""

    normalized = str(value or "").lower()
    if normalized in {"true", "si", "active", "activo", "scheduled", "programado", "open", "abierto"}:
        return "status-good"
    if normalized in {"completed", "finalizado", "closed", "cerrado", "inactive", "inactivo", "false", "no"}:
        return "status-muted"
    if normalized in {"suspended", "suspendido", "cancelled", "cancelado", "warning", "pendiente por inscripciones"}:
        return "status-warn"
    if normalized in {"en proceso", "inprogress"}:
        return "status-good"
    return "status-neutral"
