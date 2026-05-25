"""Formularios de sanciones y apelaciones.

La sancion acepta exactamente un sujeto: equipo/jugador u oficial. Esta regla se
valida aqui antes de llamar al procedimiento almacenado.

Trazabilidad:
los selects vienen de `apps.core.form_choices`; la vista entrega `cleaned_data`
a `sanction_service`, que llama procedimientos almacenados de sanciones.
"""

from django import forms

from apps.core import form_choices
from apps.core.forms import BootstrapFormMixin


TARGET_CHOICES = [
    ("team_player", "Sancionar equipo o jugador"),
    ("official", "Sancionar oficial"),
]


class SanctionForm(BootstrapFormMixin, forms.Form):
    """Captura sanciones con sujeto dinamico segun target_type."""

    target_type = forms.ChoiceField(
        label="Tipo de sancionado",
        choices=TARGET_CHOICES,
        widget=forms.RadioSelect,
        initial="team_player",
        help_text="Selecciona si la sancion aplica a un equipo/jugador o a un oficial.",
    )
    tournament_id = forms.TypedChoiceField(label="Torneo", coerce=int)
    match_id = forms.TypedChoiceField(label="Partido", coerce=int, required=False, empty_value=None)
    violation_type_id = forms.TypedChoiceField(label="Infraccion cometida", coerce=int)
    team_id = forms.TypedChoiceField(
        label="1. Equipo sancionado",
        coerce=int,
        required=False,
        empty_value=None,
        help_text="Primero selecciona el equipo. Si no eliges jugador, la sancion sera para todo el equipo.",
    )
    player_id = forms.ChoiceField(
        label="2. Jugador sancionado (opcional)",
        required=False,
        help_text="Aparecen solo los jugadores del equipo seleccionado. Dejalo vacio para sancionar al equipo.",
    )
    official_id = forms.TypedChoiceField(
        label="Oficial sancionado",
        coerce=int,
        required=False,
        empty_value=None,
        help_text="Es el oficial que recibe la sancion. El usuario que registra queda guardado por la sesion.",
    )
    sanction_type = forms.CharField(label="Medida o tipo de sancion", max_length=120)
    penalty_points = forms.IntegerField(label="Penalizacion puntos", required=False)
    penalty_games = forms.IntegerField(label="Penalizacion games", required=False)
    fine_amount = forms.DecimalField(label="Multa", required=False, max_digits=12, decimal_places=2)
    currency = forms.CharField(label="Moneda", initial="USD", max_length=10)
    notes = forms.CharField(label="Notas", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Todos los selects se alimentan desde Neon para evitar referencias
        # manuales a torneo, partido, infraccion, equipo, jugador u oficial.
        self.fields["tournament_id"].choices = form_choices.tournament_choices()
        self.fields["match_id"].choices = form_choices.match_choices()
        self.fields["violation_type_id"].choices = form_choices.violation_type_choices()
        self.fields["team_id"].choices = form_choices.team_choices()
        self.fields["player_id"].choices = form_choices.player_choices()
        self.fields["official_id"].choices = form_choices.official_choices()
        self.order_fields(
            [
                "tournament_id",
                "match_id",
                "violation_type_id",
                "target_type",
                "team_id",
                "player_id",
                "official_id",
                "sanction_type",
                "penalty_points",
                "penalty_games",
                "fine_amount",
                "currency",
                "notes",
            ]
        )

    def clean(self):
        """Garantiza un unico sancionado y consistencia jugador-equipo."""

        cleaned = super().clean()
        target_type = cleaned.get("target_type")
        player_id = cleaned.get("player_id")
        team_id = cleaned.get("team_id")
        official_id = cleaned.get("official_id")

        if target_type == "team_player":
            if not team_id:
                self.add_error("team_id", "Selecciona el equipo sancionado o el equipo donde juega el jugador.")
            elif player_id and not form_choices.player_belongs_to_team(player_id, team_id):
                self.add_error("player_id", "El jugador seleccionado no pertenece al equipo indicado.")

            if player_id:
                cleaned["team_id"] = None
            else:
                cleaned["player_id"] = ""
            cleaned["official_id"] = None
        elif target_type == "official":
            if not official_id:
                self.add_error("official_id", "Selecciona el oficial que recibe la sancion.")
            cleaned["player_id"] = ""
            cleaned["team_id"] = None
        else:
            raise forms.ValidationError("Selecciona quien recibe la sancion: equipo/jugador u oficial.")
        return cleaned


class AppealForm(BootstrapFormMixin, forms.Form):
    """Apelacion asociada a una sancion existente."""

    sanction_id = forms.TypedChoiceField(label="Sancion", coerce=int)
    filed_by_player_id = forms.ChoiceField(label="Jugador apelante", required=False)
    status = forms.CharField(label="Estado", initial="filed", max_length=80)
    notes = forms.CharField(label="Notas", widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sanction_id"].choices = form_choices.sanction_choices()
        self.fields["filed_by_player_id"].choices = form_choices.player_choices()
