"""Mixins reutilizables para formularios Django."""

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
