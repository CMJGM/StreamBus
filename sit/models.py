from django.db import models

class informe_sit(models.Model):
    idPerInforme = models.IntegerField()    
    numeroinforme = models.IntegerField()
    lugarcontrol = models.CharField(max_length=150)
    legajo = models.IntegerField()
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    empresa = models.CharField(max_length=100)
    cuit = models.CharField(max_length=13)
    domicilio = models.CharField(max_length=100)
    linea = models.CharField(max_length=10)
    ficha = models.CharField(max_length=20)
    mediocomunicacion = models.CharField(max_length=100)
    fechahoracontrol = models.DateTimeField()
    fechacomunicacion= models.DateTimeField()
    turnoafectado =  models.DateTimeField()
    descripcion =models.CharField(max_length=400)
    emisor = models.CharField(max_length=100)
    descargo = models.CharField(max_length=400)

    class Meta:
        managed = False  
        app_label = 'sit'
        db_table = 'perinformepersonal' 

        