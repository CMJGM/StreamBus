from django import forms
from .models import Sucursales

class SucursalesForm(forms.ModelForm):
    class Meta:
        model = Sucursales
        fields = ['descripcion', 'abreviatura','destinatarios_email']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'abreviatura': forms.TextInput(attrs={'class': 'form-control'}),
            'destinatarios_email': forms.TextInput(attrs={'class': 'form-control'}),
        }
