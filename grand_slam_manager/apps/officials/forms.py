"""Formularios para oficiales y asignaciones a partidos.

Trazabilidad:
`OfficialForm` alimenta `sp_create_official`; `AssignOfficialForm` toma choices
de Neon y termina en `sp_assign_official_to_match`.
"""

from django import forms

from apps.core import form_choices
from apps.core.forms import BootstrapFormMixin


class OfficialForm(BootstrapFormMixin, forms.Form):
    """Alta de juez/oficial con licencia y certificacion."""

    first_name = forms.CharField(label="Nombres", max_length=120)
    last_name = forms.CharField(label="Apellidos", max_length=120)
    nationality = forms.CharField(label="Nacionalidad", max_length=3)
    official_type = forms.CharField(label="Tipo de oficial", max_length=120)
    certification_level = forms.CharField(label="Nivel certificacion", max_length=120)
    license_number = forms.CharField(label="Licencia", max_length=120)


class AssignOfficialForm(BootstrapFormMixin, forms.Form):
    """Relaciona un oficial con un partido y rol especifico."""

    match_id = forms.TypedChoiceField(label="Partido", coerce=int)
    official_id = forms.TypedChoiceField(label="Oficial", coerce=int)
    role = forms.CharField(label="Rol en partido", max_length=120)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["match_id"].choices = form_choices.match_choices()
        self.fields["official_id"].choices = form_choices.official_choices()
