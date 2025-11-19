from django.db import models

class Categorias(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100)    
    
    def __str__(self):
        return f"{self.descripcion}"
