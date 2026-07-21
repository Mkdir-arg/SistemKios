from django.contrib.auth.forms import AuthenticationForm


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
