from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import super_admin_required

from .forms import LoginForm, UsuarioForm
from .models import User


class SistemLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


@super_admin_required
def usuarios_lista(request):
    usuarios = User.objects.select_related("punto").order_by("username")
    return render(request, "accounts/lista.html", {"usuarios": usuarios})


@super_admin_required
def usuario_crear(request):
    form = UsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario creado.")
        return redirect("accounts:usuarios_lista")
    return render(request, "accounts/form.html", {"form": form, "titulo": "Nuevo usuario"})


@super_admin_required
def usuario_editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario actualizado.")
        return redirect("accounts:usuarios_lista")
    return render(request, "accounts/form.html", {"form": form, "titulo": f"Editar {usuario.username}"})
