from django.db import models
from empleados.models import Empleado
from buses.models import Buses
from sucursales.models import Sucursales
from django.utils import timezone


class Origen(models.Model):
    """
    Modelo para gestionar los diferentes orígenes de informes.
    Permite asignar orígenes específicos a usuarios.
    """
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nombre del Origen"
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Descripción"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Si está inactivo, no aparecerá en los formularios"
    )
    orden = models.IntegerField(
        default=0,
        verbose_name="Orden de visualización"
    )

    class Meta:
        verbose_name = "Origen"
        verbose_name_plural = "Orígenes"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

def ruta_archivo(instance, filename):
    ficha = instance.informe.bus.ficha    
    fecha_hora = instance.informe.fecha_hora
    fecha_hora_str = timezone.localtime(fecha_hora).strftime("%Y%m%d_%H%M")
    return f"informes/{ficha}_{fecha_hora_str}/{filename}"


class Informe(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_hora = models.DateTimeField(default=timezone.now)
    sucursal = models.ForeignKey(Sucursales, on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, null=True, blank=True)
    bus = models.ForeignKey(Buses, on_delete=models.CASCADE)
    generado = models.BooleanField(default=False)
    origen = models.ForeignKey(
        Origen,
        on_delete=models.PROTECT,
        verbose_name="Origen",
        help_text="Origen del informe"
    )

    class Meta:
        verbose_name = "Informe"
        verbose_name_plural = "Informes"

    def __str__(self):
        return f"{self.bus.ficha} - {self.empleado.legajo if self.empleado else 'N/A'} - {self.empleado.apellido if self.empleado else 'Desconocido'} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
            

class ExpedienteInforme(models.Model):
    TIPO_CHOICES = [
        ('I', 'Informe'),
        ('S', 'Siniestro'),
        ('D', 'Desestimar'),
    ]
    informe = models.OneToOneField(Informe, on_delete=models.CASCADE, related_name='expediente')
    nro_expediente = models.IntegerField()
    comentario = models.CharField(max_length=1000, null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, null=True, blank=True)

    def __str__(self):
        tipo_display = dict(self.TIPO_CHOICES).get(self.tipo, 'Sin tipo')
        return f"Expediente {self.nro_expediente} ({tipo_display}) del Informe {self.informe.id}"

class FotoInforme(models.Model):
    informe = models.ForeignKey(Informe, related_name='fotos', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to=ruta_archivo)
    def __str__(self):
        return f"Foto de informe {self.informe.id}"    


class VideoInforme(models.Model):
    informe = models.ForeignKey(Informe, related_name='videos', on_delete=models.CASCADE)
    video = models.FileField(upload_to=ruta_archivo)
    fecha_subida = models.DateTimeField(auto_now_add=True) 


class HistorialEnvioInforme(models.Model):
    informe = models.ForeignKey(Informe, related_name='historial_envios', on_delete=models.CASCADE)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    destinatarios = models.TextField(help_text="Lista de correos separados por coma")
    
    def __str__(self):
        return f"Envío {self.fecha_envio.strftime('%d/%m/%Y %H:%M')} a {self.destinatarios}"
