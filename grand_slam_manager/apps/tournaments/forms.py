"""Formularios para estructura competitiva del torneo.

El flujo jerarquico es Tournament -> Category -> SubCategory -> Round. Las reglas
que ya estan en BD se reflejan aqui para fallar antes del procedimiento.

Trazabilidad:
choices dinamicos vienen de `apps.core.form_choices` o de filas preparadas por
`tournament_service`; al guardar, las vistas llaman `sp_create_*`/`sp_update_*`.
"""

from django import forms
from django.utils import timezone

from apps.core import form_choices
from apps.core.forms import BootstrapFormMixin

SURFACE_CHOICES = [
    ("Hard", "Hard"),
    ("Clay", "Clay"),
    ("Grass", "Grass"),
    ("Carpet", "Carpet"),
    ("Other", "Other"),
]
GENDER_CHOICES = [("M", "M"), ("F", "F")]
MODE_CHOICES = [("Singles", "Singles"), ("Doubles", "Doubles")]
BEST_OF_SETS_CHOICES = [(1, "1 set"), (3, "Mejor de 3 sets"), (5, "Mejor de 5 sets")]
DRAW_SIZE_CHOICES = [(size, f"{size} jugadores/equipos") for size in (2, 4, 8, 16, 32, 64, 128)]
TOURNAMENT_STATUS_CHOICES = [
    ("Pendiente por inscripciones", "Pendiente por inscripciones"),
    ("Activo", "Activo"),
    ("En proceso", "En proceso"),
    ("Finalizado", "Finalizado"),
]


class TournamentForm(BootstrapFormMixin, forms.Form):
    """Datos basicos de un torneo."""

    name = forms.CharField(label="Nombre", max_length=255)
    year = forms.IntegerField(label="Año")
    start_date = forms.DateField(label="Fecha inicial", widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(label="Fecha final", widget=forms.DateInput(attrs={"type": "date"}))
    location = forms.CharField(label="Dirección del torneo", max_length=255)
    surface = forms.ChoiceField(label="Superficie", choices=SURFACE_CHOICES)
    status = forms.ChoiceField(label="Estado", choices=TOURNAMENT_STATUS_CHOICES, initial="Pendiente por inscripciones")
    description = forms.CharField(label="Descripcion", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, force_pending_status: bool = False, **kwargs):
        self.force_pending_status = force_pending_status
        super().__init__(*args, **kwargs)
        current_year = timezone.localdate().year
        self.fields["year"].initial = self.initial.get("year", current_year)
        self.fields["year"].widget.attrs.setdefault("min", current_year)
        if self.force_pending_status:
            self.fields["status"].initial = "Pendiente por inscripciones"
            self.fields["status"].widget = forms.HiddenInput()

    def clean_status(self):
        if self.force_pending_status:
            return "Pendiente por inscripciones"
        return self.cleaned_data["status"]


class CourtForm(BootstrapFormMixin, forms.Form):
    """Cancha asociada a un torneo y su superficie."""

    name = forms.CharField(label="Nombre de cancha", max_length=120)
    capacity = forms.IntegerField(label="Capacidad", min_value=0)
    surface = forms.ChoiceField(label="Superficie", choices=SURFACE_CHOICES)
    indoor = forms.BooleanField(label="Cubierta/indoor", required=False)
    location = forms.CharField(label="Dirección de la cancha", max_length=255, required=False)


class CategoryForm(BootstrapFormMixin, forms.Form):
    """Categoría competitiva: género y modalidad dentro de un torneo."""

    tournament_id = forms.TypedChoiceField(label="Torneo", coerce=int)
    name = forms.CharField(label="Nombre categoría", max_length=120)
    gender = forms.ChoiceField(label="Genero", choices=GENDER_CHOICES)
    mode = forms.ChoiceField(label="Modalidad", choices=MODE_CHOICES)
    description = forms.CharField(label="Descripcion", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, tournament_id: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Cuando se entra desde un torneo especifico, la vista oculta el campo
        # para conservar la trazabilidad del filtro seleccionado.
        self.fields["tournament_id"].choices = form_choices.tournament_choices()
        if tournament_id:
            self.fields["tournament_id"].initial = tournament_id
            self.fields["tournament_id"].widget = forms.HiddenInput()


class SubCategoryForm(BootstrapFormMixin, forms.Form):
    """Cuadro competitivo que pertenece a una categoria."""

    category_id = forms.TypedChoiceField(label="Categoría", coerce=int)
    name = forms.CharField(label="Nombre cuadro", max_length=120)
    draw_size = forms.TypedChoiceField(label="Tamaño del cuadro", choices=DRAW_SIZE_CHOICES, coerce=int)
    description = forms.CharField(label="Descripcion", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, category_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_id"].choices = category_choices or form_choices.category_choices()


class RoundForm(BootstrapFormMixin, forms.Form):
    """Ronda/fase dentro de un cuadro; best_of_sets solo acepta 1, 3 o 5."""

    round_name = forms.CharField(label="Nombre ronda", max_length=120)
    subcategory_id = forms.TypedChoiceField(label="Cuadro", coerce=int)
    round_number = forms.IntegerField(label="Numero de ronda", min_value=1)
    best_of_sets = forms.TypedChoiceField(
        label="Mejor de sets",
        choices=BEST_OF_SETS_CHOICES,
        coerce=int,
        initial=3,
        help_text="La base solo permite rondas a 1, 3 o 5 sets.",
    )
    description = forms.CharField(label="Descripcion", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, subcategory_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subcategory_id"].choices = subcategory_choices or form_choices.subcategory_choices()
