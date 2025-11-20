from django import forms
from django.core.exceptions import ValidationError
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filtrar sucursales según permisos del usuario
        if user and hasattr(user, 'profile'):
            self.fields['sucursal'].queryset = user.profile.get_sucursales_permitidas()

    def clean_legajo(self):
        """Validar que el legajo no esté repetido"""
        legajo = self.cleaned_data.get('legajo')

        # Verificar si ya existe un empleado con este legajo
        empleado_existente = Empleado.objects.filter(legajo=legajo)

        # Si estamos editando, excluir el empleado actual de la validación
        if self.instance.pk:
            empleado_existente = empleado_existente.exclude(pk=self.instance.pk)

        if empleado_existente.exists():
            raise ValidationError(f'Ya existe un empleado con el legajo {legajo}. Por favor, use otro número.')

        return legajo
