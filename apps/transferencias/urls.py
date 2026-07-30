"""
La pantalla de transferencias se fusionó con la de Stock: todo el stock se opera
desde `/stock/` (modo «Transferir»), que es donde viven la vista y el endpoint.
Acá solo queda el redirect, para que los links viejos no caigan en un 404.
"""
from django.urls import path
from django.views.generic import RedirectView

app_name = "transferencias"

urlpatterns = [
    path(
        "transferencias/nueva/",
        RedirectView.as_view(pattern_name="stock:ingreso", permanent=False),
        name="nueva",
    ),
]
