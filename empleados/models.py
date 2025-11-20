from django.db import models
from categoria.models import Categorias
from sucursales.models import Sucursales

class Empleado(models.Model):
    legajo = models.IntegerField(unique=True)
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categorias, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursales, on_delete=models.CASCADE)
    fecha_ingreso = models.DateField()

    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}"

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.legajo})"
