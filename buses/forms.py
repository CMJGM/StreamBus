# forms.py en la app buses
from django import forms
from datetime import datetime
from .models import Marca, Modelo, Buses

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la marca'})
        }

class ModeloForm(forms.ModelForm):
    class Meta:
        model = Modelo
        fields = ['nombre', 'marca']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del modelo'}),
            'marca': forms.Select(attrs={'class': 'form-control'}),
        }

class BusesForm(forms.ModelForm):
    class Meta:
        model = Buses
        fields = ['ficha', 'modelo', 'ano', 'dominio']
        widgets = {
            'ficha': forms.NumberInput(attrs={'class': 'form-control'}),
            'modelo': forms.Select(attrs={'class': 'form-control'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'dominio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABC123ABC'}),
        }
    
    def clean_ficha(self):
        ficha = self.cleaned_data.get('ficha')
        if Buses.objects.filter(ficha=ficha).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un bus con esa ficha.")
        return ficha
    
    def clean_ano(self):
        ano = self.cleaned_data.get('ano')
        actual = datetime.now().year
        if ano < 1960 or ano > actual:
            raise forms.ValidationError(f"El año debe estar entre 1950 y {actual}.")
        return ano
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modelo'].queryset = Modelo.objects.select_related('marca').order_by('marca__nombre', 'nombre')

