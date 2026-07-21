from django import forms

from .models import Punto


class PuntoForm(forms.ModelForm):
    class Meta:
        model = Punto
        fields = ["nombre", "direccion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "input", "placeholder": "Ej: Kiosco Centro"}),
            "direccion": forms.TextInput(attrs={"class": "input", "placeholder": "Dirección (opcional)"}),
            "activo": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-zinc-300 text-brand-600"}),
        }
