import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import HistorialEnvioInforme
import os
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

def enviar_informe_por_mail(informe, destinatarios=None, ultimos_informes=None):
    try:
        # Si no se pasa destinatarios, se usa los destinatarios por defecto de la sucursal
        if not destinatarios:
            destinatarios = informe.sucursal.obtener_destinatarios()

        if not destinatarios:
            raise ValueError("No hay destinatarios disponibles para enviar el informe.")

        if not isinstance(destinatarios, list):
            raise ValueError("El parámetro 'destinatarios' debe ser una lista de correos.")

        # Preparar lista de fotos con CID
        fotos_con_cid = []
        for i, foto in enumerate(informe.fotos.all(), start=1):
            if foto.imagen and os.path.isfile(foto.imagen.path):
                cid = f"foto{i}"
                fotos_con_cid.append({
                    "foto": foto,
                    "cid": cid,
                })

        # Renderizar cuerpo del correo con imágenes CID
        cuerpo = render_to_string("email/informe_email.html", {
            "informe": informe,
            "fotos_con_cid": fotos_con_cid,
            "ultimos_informes": ultimos_informes or [],
        })

        # Crear el correo
        email = EmailMessage(
            subject=f"ALARMA -> Ficha : {informe.bus.ficha} - {informe.fecha_hora.strftime('%d/%m/%Y %H:%M')}",
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        email.content_subtype = "html"  # Enviar como HTML

        # Adjuntar las imágenes al email con su Content-ID
        for item in fotos_con_cid:
            with open(item["foto"].imagen.path, "rb") as f:
                image = MIMEImage(f.read())
                image.add_header('Content-ID', f"<{item['cid']}>")
                image.add_header('Content-Disposition', 'inline')
                email.attach(image)

        # Guardar historial de envío
        HistorialEnvioInforme.objects.create(
            informe=informe,
            destinatarios=", ".join(destinatarios),
        )

        email.send()
        logger.info(f"Correo enviado correctamente a {destinatarios}")

    except Exception as e:
        logger.error(f"Error al enviar el informe por email: {e}")
        raise
