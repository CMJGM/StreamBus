from django.db import models

class Sucursales(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    abreviatura = models.CharField(max_length=3)
    destinatarios_email = models.TextField(
        blank=True, 
        help_text="Lista de correos electrónicos separados por coma, por ejemplo: correo1@dominio.com, correo2@dominio.com"
    )    
    
    def __str__(self):
        return f"{self.abreviatura}  -  {self.descripcion}"

    def obtener_destinatarios(self):
        return [email.strip() for email in self.destinatarios_email.split(',')] if self.destinatarios_email else []