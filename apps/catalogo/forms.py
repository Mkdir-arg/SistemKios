from django import forms

from .models import Producto


class ProductoForm(forms.ModelForm):
    nueva_categoria = forms.CharField(
        label="…o crear nueva categoría",
        required=False,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Nombre de la categoría nueva"}),
    )

    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "nueva_categoria", "costo", "alicuota_iva", "activo"]
        field_order = ["nombre", "categoria", "nueva_categoria", "costo", "alicuota_iva", "activo"]
        labels = {"alicuota_iva": "Alícuota IVA (%)"}
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "input", "placeholder": "Ej: Coca-Cola 500ml"}),
            "categoria": forms.Select(attrs={"class": "input"}),
            "costo": forms.NumberInput(attrs={"class": "input tnum", "step": "0.01", "min": "0"}),
            "alicuota_iva": forms.NumberInput(attrs={"class": "input tnum", "step": "0.01", "min": "0"}),
            "activo": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-zinc-300 text-brand-600"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].required = False
        self.fields["categoria"].empty_label = "— (sin categoría)"
