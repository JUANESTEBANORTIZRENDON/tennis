"""Formularios de acceso y administracion de usuarios internos.

Mantienen solo validaciones de entrada; la autenticacion y escritura real vive en
`apps.accounts.services.user_service`.

Trazabilidad:
la vista instancia el formulario, valida `cleaned_data` y entrega esos datos al
servicio; el formulario no consulta Neon salvo choices recibidos desde la vista.
"""

from django import forms

from apps.core.forms import BootstrapFormMixin


class LoginForm(BootstrapFormMixin, forms.Form):
    """Credenciales basicas para iniciar sesion antes del 2FA opcional."""

    email = forms.EmailField(label="Correo electronico")
    password = forms.CharField(label="Contrasena", widget=forms.PasswordInput)


class TwoFactorForm(BootstrapFormMixin, forms.Form):
    """Codigo corto enviado por correo cuando EMAIL_2FA_ENABLED esta activo."""

    code = forms.CharField(label="Codigo de verificacion", min_length=6, max_length=6)


class UserCreateForm(BootstrapFormMixin, forms.Form):
    """Alta manual de cuentas internas desde el panel administrador."""

    email = forms.EmailField(label="Correo electronico")
    full_name = forms.CharField(label="Nombre completo", max_length=255)
    phone = forms.CharField(label="Telefono", max_length=50, required=False)
    password = forms.CharField(label="Contrasena temporal", widget=forms.PasswordInput)
    role_id = forms.ChoiceField(label="Rol")
    is_active = forms.BooleanField(label="Cuenta activa", required=False, initial=True)

    def __init__(self, *args, role_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role_id"].choices = role_choices or []


class UserPasswordChangeForm(BootstrapFormMixin, forms.Form):
    """Cambio administrativo de contrasena para una cuenta existente."""

    password = forms.CharField(label="Nueva contrasena", min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirmar contrasena", min_length=8, widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("confirm_password") and cleaned["password"] != cleaned["confirm_password"]:
            raise forms.ValidationError("Las contrasenas no coinciden.")
        return cleaned
