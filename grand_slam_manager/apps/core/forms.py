"""Mixins y formularios reutilizables del panel."""

from django import forms


class BootstrapFormMixin:
    """Aplica clases Bootstrap sin romper widgets compuestos como RadioSelect."""

    def __init__(self, *args, **kwargs):
        """Normaliza clases visuales al instanciar cada formulario."""

        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = "form-check-input" if isinstance(widget, forms.CheckboxInput) else "form-control"
            if isinstance(widget, forms.RadioSelect):
                css_class = ""
            if isinstance(widget, forms.Select):
                css_class = "form-select"
            existing = widget.attrs.get("class", "")
            combined = f"{existing} {css_class}".strip()
            if combined:
                widget.attrs["class"] = combined
            else:
                widget.attrs.pop("class", None)


class AdminRowForm(BootstrapFormMixin, forms.Form):
    """Formulario dinamico para el CRUD administrador.

    Las columnas vienen desde `sp_admin_table_columns_json`; la vista solo
    entrega los metadatos y este formulario normaliza valores para el
    procedimiento almacenado generico.
    """

    def __init__(self, *args, columns=None, row=None, mode="create", **kwargs):
        self.columns = columns or []
        self.row = row or {}
        self.mode = mode
        super().__init__(*args, **kwargs)
        for column in self.columns:
            name = str(column.get("column_name") or "")
            if not name:
                continue
            is_pk = bool(column.get("is_primary_key"))
            is_identity = bool(column.get("is_identity"))
            has_default = column.get("column_default") not in (None, "")
            data_type = str(column.get("data_type") or "").lower()
            required = not bool(column.get("nullable")) and not has_default and not is_identity

            if self.mode == "edit" and is_pk:
                continue
            if self.mode == "create" and is_identity:
                continue

            initial = self.row.get(name)
            field = self._field_for_column(name, data_type, required, initial)
            self._style_field(field)
            self.fields[name] = field

    def _style_field(self, field):
        widget = field.widget
        css_class = "form-check-input" if isinstance(widget, forms.CheckboxInput) else "form-control"
        if isinstance(widget, forms.Select):
            css_class = "form-select"
        existing = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{existing} {css_class}".strip()

    def _field_for_column(self, name: str, data_type: str, required: bool, initial):
        label = name.replace("_", " ").title()
        if data_type == "boolean":
            return forms.BooleanField(label=label, required=False, initial=bool(initial))
        if "date" in data_type and "time" not in data_type:
            return forms.DateField(
                label=label,
                required=required,
                initial=initial,
                widget=forms.DateInput(attrs={"type": "date"}),
            )
        if "timestamp" in data_type or data_type == "time without time zone":
            return forms.DateTimeField(
                label=label,
                required=required,
                initial=initial,
                widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
            )
        if data_type in {"integer", "bigint", "smallint"}:
            return forms.IntegerField(label=label, required=required, initial=initial)
        if data_type in {"numeric", "double precision", "real"}:
            return forms.DecimalField(label=label, required=required, initial=initial)
        widget = forms.Textarea(attrs={"rows": 3}) if "text" in data_type or name.lower() in {"notes", "description", "biography"} else forms.TextInput()
        return forms.CharField(label=label, required=required, initial=initial, widget=widget)

    def payload(self) -> dict:
        """Devuelve datos limpios sin valores vacios."""

        payload = {}
        for key, value in self.cleaned_data.items():
            if value in ("", None):
                continue
            payload[key] = value
        return payload
