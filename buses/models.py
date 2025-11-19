from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime

class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Modelo(models.Model):
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.marca.nombre} {self.nombre}"

def validate_ano(value):
    current_year = datetime.now().year
    if value < 1960 or value > current_year:
        raise ValidationError(f"El año debe estar entre 1960 y {current_year}.")
    
class Buses(models.Model):
    ficha = models.IntegerField(unique=True)
    modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE)
    ano = models.IntegerField()
    dominio = models.CharField(max_length=10, unique=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    estado = models.BooleanField(default=True)


    class Meta:
        verbose_name = "Bus"
        verbose_name_plural = "Buses"

    def __str__(self):
        return f"{self.ficha} : {self.modelo} ({self.ano}) - {self.dominio}"
