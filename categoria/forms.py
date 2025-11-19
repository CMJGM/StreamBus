
from django import forms
from .models import Categorias

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categorias
        fields = ['descripcion']
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la categoría',
            })
        }
