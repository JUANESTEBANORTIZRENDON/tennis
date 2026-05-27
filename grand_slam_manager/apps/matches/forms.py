"""Formularios de match center y programacion.

Trazabilidad:
los campos seleccionables se cargan desde `form_choices` o desde
`match_service.team_choices_for_match`; las vistas envian `cleaned_data` a
procedimientos `sp_*` de partido y agenda operativa.
"""

from django import forms

from apps.core import form_choices
from apps.core.forms import BootstrapFormMixin

MATCH_STATUS_CHOICES = [
    ("Scheduled", "Scheduled"),
    ("InProgress", "InProgress"),
    ("Completed", "Completed"),
    ("Retired", "Retired"),
    ("Walkover", "Walkover"),
    ("Suspended", "Suspended"),
    ("Cancelled", "Cancelled"),
    ("Disqualified", "Disqualified"),
]


class MatchForm(BootstrapFormMixin, forms.Form):
    """Creacion inicial de un partido."""

    round_id = forms.TypedChoiceField(label="Ronda", coerce=int)
    scheduled_datetime = forms.DateTimeField(label="Fecha y hora", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    court_id = forms.TypedChoiceField(label="Cancha", coerce=int)
    status = forms.ChoiceField(label="Estado", choices=MATCH_STATUS_CHOICES, initial="Scheduled")

    def __init__(self, *args, round_choices=None, court_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # La vista puede inyectar rondas/canchas filtradas por torneo.
        self.fields["round_id"].choices = round_choices or form_choices.round_choices()
        self.fields["court_id"].choices = court_choices or form_choices.court_choices()


class MatchParticipantForm(BootstrapFormMixin, forms.Form):
    """Agrega equipo al lado A o B de un partido."""

    team_id = forms.TypedChoiceField(label="Equipo", coerce=int)
    side = forms.ChoiceField(label="Lado", choices=[("A", "A"), ("B", "B")])

    def __init__(self, *args, team_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # `team_choices` suele venir filtrado por la ronda del partido.
        self.fields["team_id"].choices = team_choices or form_choices.team_choices()


class MatchSetForm(BootstrapFormMixin, forms.Form):
    """Registra marcador de un set y su ganador."""

    set_number = forms.IntegerField(label="Set", min_value=1)
    team_a_games = forms.IntegerField(label="Games equipo A", min_value=0)
    team_b_games = forms.IntegerField(label="Games equipo B", min_value=0)
    tie_break_a = forms.IntegerField(label="Tiebreak A", min_value=0, required=False)
    tie_break_b = forms.IntegerField(label="Tiebreak B", min_value=0, required=False)
    winner_team_id = forms.TypedChoiceField(label="Ganador del set", coerce=int)

    def __init__(self, *args, team_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["winner_team_id"].choices = team_choices or form_choices.team_choices()


class FinishMatchForm(BootstrapFormMixin, forms.Form):
    """Finaliza un partido indicando equipo ganador."""

    winning_team_id = forms.TypedChoiceField(label="Equipo ganador", coerce=int)

    def __init__(self, *args, team_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["winning_team_id"].choices = team_choices or form_choices.team_choices()


class ScheduleMatchForm(BootstrapFormMixin, forms.Form):
    """Programa fecha, hora y cancha de un partido."""

    round_id = forms.TypedChoiceField(label="Ronda", coerce=int)
    scheduled_datetime = forms.DateTimeField(label="Fecha y hora", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    court_id = forms.TypedChoiceField(label="Cancha", coerce=int)

    def __init__(self, *args, round_choices=None, court_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["round_id"].choices = round_choices or form_choices.round_choices()
        self.fields["court_id"].choices = court_choices or form_choices.court_choices()


class ScheduleAssignmentForm(BootstrapFormMixin, forms.Form):
    """Asigna fecha y cancha a un partido ya creado."""

    match_id = forms.TypedChoiceField(label="Partido", coerce=int)
    scheduled_datetime = forms.DateTimeField(label="Fecha y hora", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    court_id = forms.TypedChoiceField(label="Cancha", coerce=int)

    def __init__(self, *args, match_choices=None, court_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["match_id"].choices = match_choices or form_choices.match_choices()
        self.fields["court_id"].choices = court_choices or form_choices.court_choices()


class RescheduleMatchForm(BootstrapFormMixin, forms.Form):
    """Reprograma un partido y guarda motivo operativo."""

    new_datetime = forms.DateTimeField(label="Nueva fecha y hora", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    new_court_id = forms.TypedChoiceField(label="Nueva cancha", coerce=int)
    reason = forms.CharField(label="Motivo", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_court_id"].choices = form_choices.court_choices()

