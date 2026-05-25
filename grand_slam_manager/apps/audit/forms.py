"""Filtros del visor de auditoria."""

from django import forms

from apps.core import form_choices
from apps.core.forms import BootstrapFormMixin


class AuditFilterForm(BootstrapFormMixin, forms.Form):
    """Permite acotar auditoria por usuario, torneo, entidad o texto libre."""

    user_id = forms.TypedChoiceField(label="Usuario", coerce=int, required=False, empty_value=None)
    tournament_id = forms.TypedChoiceField(label="Torneo", coerce=int, required=False, empty_value=None)
    entity_name = forms.CharField(label="Entidad", required=False)
    q = forms.CharField(label="Busqueda", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_id"].choices = form_choices.user_choices()
        self.fields["tournament_id"].choices = form_choices.tournament_choices()
