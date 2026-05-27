"""Formularios de jugadores, lesiones, equipos e inscripciones.

Trazabilidad:
los choices salen de `apps.core.form_choices` o de servicios que filtran por
torneo/cuadro; las vistas envian `cleaned_data` a `player_service`.
"""

from datetime import timedelta

from django import forms
from django.utils import timezone

from apps.core import form_choices
from apps.core.forms import BootstrapFormMixin

GENDER_CHOICES = [("M", "M"), ("F", "F")]
HAND_CHOICES = [("R", "R"), ("L", "L"), ("A", "A")]
DOCUMENT_TYPE_CHOICES = [("Passport", "Pasaporte"), ("National ID", "Documento nacional"), ("Citizenship Card", "Cedula"), ("Identity Card", "Tarjeta de identidad"), ("Foreign ID", "Documento extranjero"), ("Driver License", "Licencia de conduccion")]
COUNTRY_CHOICES = [("", "Seleccione un pais"), ("ARG", "Argentina"), ("AUS", "Australia"), ("BRA", "Brasil"), ("CAN", "Canada"), ("CHL", "Chile"), ("CHN", "China"), ("COL", "Colombia"), ("CRI", "Costa Rica"), ("CUB", "Cuba"), ("ECU", "Ecuador"), ("ESP", "Espana"), ("FRA", "Francia"), ("DEU", "Alemania"), ("GBR", "Reino Unido"), ("IND", "India"), ("ITA", "Italia"), ("JPN", "Japon"), ("KOR", "Corea del Sur"), ("MEX", "Mexico"), ("NLD", "Paises Bajos"), ("PAN", "Panama"), ("PER", "Peru"), ("PRT", "Portugal"), ("RUS", "Rusia"), ("SRB", "Serbia"), ("SWE", "Suecia"), ("CHE", "Suiza"), ("URY", "Uruguay"), ("USA", "Estados Unidos"), ("VEN", "Venezuela")]
QUALIFYING_METHOD_CHOICES = [
    ("Direct", "Directo"),
    ("Wildcard", "Invitación"),
    ("Qualifier", "Clasificación"),
    ("Lucky Loser", "Lucky Loser"),
    ("Protected Ranking", "Ranking protegido"),
]


class PlayerForm(BootstrapFormMixin, forms.Form):
    """Registro completo de jugador que alimenta sp_create_player."""

    id = forms.CharField(label="ID jugador/documento", max_length=80)
    document_type = forms.ChoiceField(label="Tipo documento", choices=DOCUMENT_TYPE_CHOICES)
    issuer_country = forms.ChoiceField(label="Pais emisor", choices=COUNTRY_CHOICES)
    first_name = forms.CharField(label="Nombres", max_length=120)
    last_name = forms.CharField(label="Apellidos", max_length=120)
    gender = forms.ChoiceField(label="Genero", choices=GENDER_CHOICES)
    birth_date = forms.DateField(label="Fecha nacimiento", widget=forms.DateInput(attrs={"type": "date"}))
    country_code = forms.ChoiceField(label="Pais deportivo", choices=COUNTRY_CHOICES)
    height_cm = forms.IntegerField(label="Estatura cm", required=False)
    weight_kg = forms.IntegerField(label="Peso kg", required=False)
    hand = forms.ChoiceField(label="Mano", choices=HAND_CHOICES)
    turned_pro_year = forms.IntegerField(label="Ano profesional", required=False)
    biography = forms.CharField(label="Biografia", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        if birth_date > timezone.localdate() - timedelta(days=15 * 365):
            raise forms.ValidationError("El jugador debe tener minimo 15 anos.")
        return birth_date


class InjuryRegistrationForm(BootstrapFormMixin, forms.Form):
    """Asigna una lesion existente o crea una nueva antes de asignarla."""

    player_id = forms.ChoiceField(label="Jugador")
    injury_id = forms.TypedChoiceField(label="Lesión existente", coerce=int, required=False, empty_value=None)
    injury_type_id = forms.TypedChoiceField(label="Tipo lesión", coerce=int, required=False, empty_value=None)
    injury_date = forms.DateField(label="Fecha lesión", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(label="Descripcion", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Las opciones se alimentan de Neon para evitar escribir IDs a mano.
        self.fields["player_id"].choices = form_choices.player_choices()
        self.fields["injury_id"].choices = form_choices.injury_choices()
        self.fields["injury_type_id"].choices = form_choices.injury_type_choices()

    def clean(self):
        """Exige una fuente valida de lesion: existente o tipo nuevo."""

        cleaned = super().clean()
        if not cleaned.get("injury_id") and not cleaned.get("injury_type_id"):
            raise forms.ValidationError("Indica una lesión existente o un tipo de lesión para crear una nueva.")
        return cleaned


class CloseInjuryForm(BootstrapFormMixin, forms.Form):
    """Cierre de lesión con fecha de recuperación."""

    injury_id = forms.TypedChoiceField(label="Lesión", coerce=int)
    recovery_date = forms.DateField(label="Fecha recuperación", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["injury_id"].choices = form_choices.injury_choices()


class TeamForm(BootstrapFormMixin, forms.Form):
    """Equipo competitivo: puede representar singles o doubles."""

    name = forms.CharField(label="Nombre equipo", max_length=255)
    notes = forms.CharField(label="Notas", required=False, widget=forms.Textarea(attrs={"rows": 2}))


class TeamMemberForm(BootstrapFormMixin, forms.Form):
    """Relaciona jugadores con equipos."""

    team_id = forms.TypedChoiceField(label="Equipo", coerce=int)
    player_id = forms.ChoiceField(label="Jugador")
    role = forms.CharField(label="Rol", initial="Player", max_length=80, widget=forms.HiddenInput())
    start_date = forms.DateField(label="Fecha inicio", widget=forms.DateInput(attrs={"type": "date"}), initial=timezone.localdate)

    def __init__(self, *args, team_choices=None, player_choices=None, selected_team_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # La vista puede pasar choices filtrados para mostrar solo jugadores
        # que aun no pertenecen al equipo seleccionado.
        self.fields["team_id"].choices = team_choices or form_choices.team_choices()
        self.fields["player_id"].choices = player_choices or form_choices.player_choices()
        if selected_team_id:
            self.fields["team_id"].initial = selected_team_id


class CoachForm(BootstrapFormMixin, forms.Form):
    """Crea entrenadores vinculados a un unico equipo."""

    team_id = forms.TypedChoiceField(label="Equipo", coerce=int)
    first_name = forms.CharField(label="Nombres", max_length=80)
    last_name = forms.CharField(label="Apellidos", max_length=80)
    nationality = forms.CharField(label="Nacionalidad", max_length=3)
    birth_date = forms.DateField(label="Fecha nacimiento", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    license_number = forms.CharField(label="Licencia", max_length=50, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team_id"].choices = form_choices.team_choices()


class CoachAssignmentForm(BootstrapFormMixin, forms.Form):
    """Asigna jugadores al entrenador respetando el equipo del entrenador."""

    coach_id = forms.TypedChoiceField(label="Entrenador", coerce=int)
    player_id = forms.ChoiceField(label="Jugador")
    start_date = forms.DateField(label="Fecha inicio", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, coach_choices=None, player_choices=None, selected_coach_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["coach_id"].choices = coach_choices or form_choices.coach_choices()
        self.fields["player_id"].choices = player_choices or form_choices.player_choices()
        if selected_coach_id:
            self.fields["coach_id"].initial = selected_coach_id


class EntryForm(BootstrapFormMixin, forms.Form):
    """Inscripción de un equipo dentro de un cuadro competitivo."""

    subcategory_id = forms.TypedChoiceField(label="Cuadro", coerce=int)
    team_id = forms.TypedChoiceField(label="Equipo", coerce=int)
    qualifying_method = forms.ChoiceField(label="Método clasificación", choices=QUALIFYING_METHOD_CHOICES, initial="Direct")

    def __init__(self, *args, subcategory_choices=None, team_choices=None, fixed_subcategory_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # En inscripciones, la vista pasa cuadros/equipos filtrados por torneo
        # para que el procedimiento reciba IDs coherentes.
        self.fields["subcategory_id"].choices = subcategory_choices or form_choices.subcategory_choices()
        self.fields["team_id"].choices = team_choices or form_choices.team_choices()
        if fixed_subcategory_id:
            self.fields["subcategory_id"].initial = fixed_subcategory_id
            self.fields["subcategory_id"].widget = forms.HiddenInput()


class EntryPlayerForm(BootstrapFormMixin, forms.Form):
    """Agrega jugadores a equipos que ya estan inscritos en un cuadro."""

    subcategory_id = forms.TypedChoiceField(label="Cuadro", coerce=int)
    team_id = forms.TypedChoiceField(label="Equipo inscrito", coerce=int)
    player_id = forms.ChoiceField(label="Jugador")

    def __init__(
        self,
        *args,
        subcategory_choices=None,
        entered_team_choices=None,
        player_choices=None,
        fixed_subcategory_id=None,
        fixed_team_id=None,
        hide_team_field=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["subcategory_id"].choices = subcategory_choices or form_choices.subcategory_choices()
        self.fields["team_id"].choices = entered_team_choices or form_choices.team_choices()
        self.fields["player_id"].choices = player_choices or form_choices.player_choices()
        if fixed_subcategory_id:
            self.fields["subcategory_id"].initial = fixed_subcategory_id
            self.fields["subcategory_id"].widget = forms.HiddenInput()
        if fixed_team_id:
            self.fields["team_id"].initial = fixed_team_id
        if fixed_team_id or hide_team_field:
            self.fields["team_id"].widget = forms.HiddenInput()
