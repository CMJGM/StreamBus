from django import forms
from .models import Empleado
from categoria.models import Categorias
from sucursales.models import Sucursales


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['legajo', 'apellido', 'nombre', 'categoria', 'sucursal', 'fecha_ingreso']
    
    legajo = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': 'form-control', 'placeholder': 'Ingrese el legajo'
    }))
    apellido = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Ingrese el apellido'
    }))
    nombre = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Ingrese el nombre'
    }))
    categoria = forms.ModelChoiceField(queryset=Categorias.objects.all(), widget=forms.Select(attrs={
        'class': 'form-control'
    }))
    sucursal = forms.ModelChoiceField(queryset=Sucursales.objects.all(), widget=forms.Select(attrs={
        'class': 'form-control'
    }))
    fecha_ingreso = forms.DateField(widget=forms.DateInput(attrs={
        'class': 'form-control', 'placeholder': 'DD/MM/YYYY', 'type': 'date'
    }))
