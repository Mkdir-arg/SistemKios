from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.puntos.models import Punto

from .models import User


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
        help_text="En edición, dejala vacía para no cambiarla.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "rol", "punto", "is_active"]
        field_order = ["username", "first_name", "last_name", "rol", "punto", "password", "is_active"]
        labels = {"is_active": "Activo"}
        widgets = {
            "username": forms.TextInput(attrs={"class": "input", "autocomplete": "off"}),
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "rol": forms.Select(attrs={"class": "input"}),
            "punto": forms.Select(attrs={"class": "input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-zinc-300 text-brand-600"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["punto"].queryset = Punto.objects.filter(activo=True)
        self.fields["punto"].required = False
        self.fields["punto"].empty_label = "— (sin punto)"
        # La contraseña es obligatoria al crear, opcional al editar.
        if self.instance.pk is None:
            self.fields["password"].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("rol") == User.Rol.VENDEDOR and not cleaned.get("punto"):
            self.add_error("punto", "Asignale un punto al vendedor.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Formulario de ingreso con estilos propios (clase `input` del design system)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "input",
                "placeholder": "Usuario",
                "autofocus": True,
                "autocomplete": "username",
            }
        )
        self.fields["username"].label = "Usuario"
        self.fields["password"].widget.attrs.update(
            {
                "class": "input",
                "placeholder": "Contraseña",
                "autocomplete": "current-password",
            }
        )
        self.fields["password"].label = "Contraseña"

    error_messages = {
        "invalid_login": "Usuario o contraseña incorrectos. Probá de nuevo.",
        "inactive": "Esta cuenta está desactivada.",
    }
