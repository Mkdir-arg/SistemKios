from django.contrib.auth.views import LoginView

from .forms import LoginForm


class SistemLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True
