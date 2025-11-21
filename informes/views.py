import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count
from django.urls import reverse_lazy
from django.utils import timezone

logger = logging.getLogger('informes.views')
from django.utils.timezone import now
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.utils.http import urlencode
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView,FormView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from usuarios.mixins import InformeFilterMixin, SucursalAccessMixin, SucursalFormMixin

from .decorators import check_sucursal_access, audit_file_access
from .models import Informe,FotoInforme, VideoInforme, HistorialEnvioInforme, Buses, Sucursales, ExpedienteInforme
from sucursales.models import Sucursales
from empleados.models import Empleado
from buses.models import Buses
from collections import defaultdict

from .forms import InformeForm
from .forms import InformeFiltroForm
from .forms import FotoInformeForm, VideoForm, InformeGuardia
from .forms import EnviarInformeEmailForm

from .utils import enviar_informe_por_mail 
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode

import os
import json
import locale
import requests

try:
    locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252') 
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')

from calendar import month_name

class ListaInformesBorrarView(LoginRequiredMixin, View):
   template_name = 'informes/lista_borrar.html'

   def get(self, request):
       informes = Informe.objects.all().order_by('-id').prefetch_related('fotos')
       id_desde = request.GET.get('id_desde')
       id_hasta = request.GET.get('id_hasta')

       if id_desde and id_hasta:
          try:
            id_desde = int(id_desde)
            id_hasta = int(id_hasta)
            informes = informes.filter(id__gte=id_desde, id__lte=id_hasta).order_by('-id').prefetch_related('fotos')
          except ValueError:
                pass
       else:
            informes = informes[:20]

       context = {'informes': informes}
       return render(request, self.template_name, context)

class InformeCreateSistemas(SucursalFormMixin, CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_sistemas.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        from .models import Origen
        # Obtener el origen "Sistemas"
        try:
            origen_sistemas = Origen.objects.get(nombre='Sistemas')
            origen_id = origen_sistemas.id
        except Origen.DoesNotExist:
            origen_id = None

        return {
            'origen': origen_id,
            'fecha_hora': timezone.now(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_video_size_mb'] = settings.MAX_VIDEO_UPLOAD_SIZE_MB
        context['max_image_size_mb'] = getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE_MB', 10)
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Permitir todos los buses y empleados (la selección se hace por AJAX)
        form.fields['bus'].queryset = Buses.objects.filter(estado=True).order_by('ficha')
        form.fields['bus'].required = True
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['empleado'].required = False
        form.fields['titulo'].required = True
        form.fields['descripcion'].required = True
        form.fields['sucursal'].required = True
        form.fields['fecha_hora'].required = True
        form.fields['fecha_hora'].widget.attrs.update({
            'type': 'datetime-local',
            'class': 'form-control form-control-sm',
        })
        return form

    def form_invalid(self, form):
        # Log de errores para debug
        logger.error(f"Form errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def form_valid(self, form):
        from .validators import validate_image_file, validate_video_file, convert_video_to_h264, get_video_info_ffprobe, needs_conversion

        self.object = form.save()
        informe = self.object
        conversion_messages = []

        # Validar y subir imágenes
        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            try:
                validate_image_file(img)
                id_formateado = str(informe.id).zfill(10)
                numero_imagen = str(index).zfill(3)
                extension = os.path.splitext(img.name)[1].lower() or ".jpg"
                nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

                foto = FotoInforme(informe=informe)
                foto.imagen.save(nombre_archivo, ContentFile(img.read()))
                foto.save()
            except Exception as e:
                logger.error(f"Error validando imagen {img.name}: {e}")
                messages.warning(self.request, f"Imagen {img.name} no válida: {str(e)}")

        # Validar, subir y convertir videos
        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            try:
                validate_video_file(vid, validate_codec=False)
                id_formateado = str(informe.id).zfill(10)
                numero_video = str(index).zfill(3)
                nombre_archivo = f"V{id_formateado}{numero_video}.mp4"

                video = VideoInforme(informe=informe)
                video.video.save(nombre_archivo, ContentFile(vid.read()))
                video.save()

                # Verificar y convertir si es necesario
                video_path = video.video.path
                video_info = get_video_info_ffprobe(video_path)
                if video_info and needs_conversion(video_info):
                    logger.info(f"Convirtiendo video {vid.name} de {video_info.get('video_codec')} a H.264")
                    result = convert_video_to_h264(video_path)
                    if result['success'] and result.get('converted'):
                        conversion_messages.append(f"Video {vid.name} convertido de {result['original_codec'].upper()} a H.264")
                        if result['output_path'] != video_path:
                            new_relative_path = os.path.relpath(result['output_path'], settings.MEDIA_ROOT)
                            video.video.name = new_relative_path
                            video.save()
            except Exception as e:
                logger.error(f"Error procesando video {vid.name}: {e}")
                messages.warning(self.request, f"Video {vid.name} no válido: {str(e)}")

        if conversion_messages:
            messages.info(self.request, " | ".join(conversion_messages))

        messages.success(self.request, f"Informe #{informe.id} creado correctamente.")
        return super().form_valid(form)

class InformeCreateGuardia(SucursalFormMixin, CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_guardia.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        from .models import Origen
        try:
            origen_obj = Origen.objects.get(nombre='Guardia')
            origen_id = origen_obj.id
        except Origen.DoesNotExist:
            origen_id = None
        return {
            'origen': origen_id,
            'fecha_hora': timezone.now(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_video_size_mb'] = settings.MAX_VIDEO_UPLOAD_SIZE_MB
        context['max_image_size_mb'] = getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE_MB', 10)
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.filter(estado=True).order_by('ficha')
        form.fields['bus'].required = True
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['empleado'].required = False
        form.fields['titulo'].required = True
        form.fields['descripcion'].required = True
        form.fields['sucursal'].required = True
        form.fields['fecha_hora'].required = True
        form.fields['fecha_hora'].widget.attrs.update({
            'type': 'datetime-local',
            'class': 'form-control form-control-sm',
        })
        return form

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def form_valid(self, form):
        from .validators import validate_image_file, validate_video_file, convert_video_to_h264, get_video_info_ffprobe, needs_conversion

        self.object = form.save()
        informe = self.object

        # Validar y subir imágenes
        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            try:
                validate_image_file(img)
                id_formateado = str(informe.id).zfill(10)
                numero_imagen = str(index).zfill(3)
                extension = os.path.splitext(img.name)[1].lower() or ".jpg"
                nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

                foto = FotoInforme(informe=informe)
                foto.imagen.save(nombre_archivo, ContentFile(img.read()))
                foto.save()
            except Exception as e:
                logger.error(f"Error validando imagen {img.name}: {e}")
                messages.warning(self.request, f"Imagen {img.name} no válida: {str(e)}")

        # Validar, subir y convertir videos
        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            try:
                validate_video_file(vid, validate_codec=False)
                id_formateado = str(informe.id).zfill(10)
                numero_video = str(index).zfill(3)
                nombre_archivo = f"V{id_formateado}{numero_video}.mp4"

                video = VideoInforme(informe=informe)
                video.video.save(nombre_archivo, ContentFile(vid.read()))
                video.save()

                # Verificar si necesita conversión
                video_path = video.video.path
                video_info = get_video_info_ffprobe(video_path)
                if video_info and needs_conversion(video_info):
                    logger.info(f"Convirtiendo video {vid.name} de {video_info.get('video_codec')} a H.264")
                    success = convert_video_to_h264(video_path)
                    if success:
                        logger.info(f"Video {vid.name} convertido exitosamente")
                    else:
                        logger.warning(f"No se pudo convertir el video {vid.name}")
            except Exception as e:
                logger.error(f"Error procesando video {vid.name}: {e}")
                messages.warning(self.request, f"Video {vid.name} no válido: {str(e)}")

        return super().form_valid(form)

class InformeCreateSiniestros(SucursalFormMixin, CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_siniestro.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        from .models import Origen
        try:
            origen_obj = Origen.objects.get(nombre='Siniestros')
            origen_id = origen_obj.id
        except Origen.DoesNotExist:
            origen_id = None
        return {
            'origen': origen_id,
            'fecha_hora': timezone.now(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_video_size_mb'] = settings.MAX_VIDEO_UPLOAD_SIZE_MB
        context['max_image_size_mb'] = getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE_MB', 10)
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.filter(estado=True).order_by('ficha')
        form.fields['bus'].required = True
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['empleado'].required = False
        form.fields['titulo'].required = True
        form.fields['descripcion'].required = True
        form.fields['sucursal'].required = True
        form.fields['fecha_hora'].required = True
        form.fields['fecha_hora'].widget.attrs.update({
            'type': 'datetime-local',
            'class': 'form-control form-control-sm',
        })
        return form

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def form_valid(self, form):
        from .validators import validate_image_file, validate_video_file, convert_video_to_h264, get_video_info_ffprobe, needs_conversion

        self.object = form.save()
        informe = self.object

        # Validar y subir imágenes
        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            try:
                validate_image_file(img)
                id_formateado = str(informe.id).zfill(10)
                numero_imagen = str(index).zfill(3)
                extension = os.path.splitext(img.name)[1].lower() or ".jpg"
                nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

                foto = FotoInforme(informe=informe)
                foto.imagen.save(nombre_archivo, ContentFile(img.read()))
                foto.save()
            except Exception as e:
                logger.error(f"Error validando imagen {img.name}: {e}")
                messages.warning(self.request, f"Imagen {img.name} no válida: {str(e)}")

        # Validar, subir y convertir videos
        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            try:
                validate_video_file(vid, validate_codec=False)
                id_formateado = str(informe.id).zfill(10)
                numero_video = str(index).zfill(3)
                nombre_archivo = f"V{id_formateado}{numero_video}.mp4"

                video = VideoInforme(informe=informe)
                video.video.save(nombre_archivo, ContentFile(vid.read()))
                video.save()

                # Verificar si necesita conversión
                video_path = video.video.path
                video_info = get_video_info_ffprobe(video_path)
                if video_info and needs_conversion(video_info):
                    logger.info(f"Convirtiendo video {vid.name} de {video_info.get('video_codec')} a H.264")
                    success = convert_video_to_h264(video_path)
                    if success:
                        logger.info(f"Video {vid.name} convertido exitosamente")
                    else:
                        logger.warning(f"No se pudo convertir el video {vid.name}")
            except Exception as e:
                logger.error(f"Error procesando video {vid.name}: {e}")
                messages.warning(self.request, f"Video {vid.name} no válido: {str(e)}")

        return super().form_valid(form)

class InformeCreateTaller(SucursalFormMixin, CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_taller.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        from .models import Origen
        try:
            origen_obj = Origen.objects.get(nombre='Taller')
            origen_id = origen_obj.id
        except Origen.DoesNotExist:
            origen_id = None
        return {
            'origen': origen_id,
            'fecha_hora': timezone.now(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_video_size_mb'] = settings.MAX_VIDEO_UPLOAD_SIZE_MB
        context['max_image_size_mb'] = getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE_MB', 10)
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.filter(estado=True).order_by('ficha')
        form.fields['bus'].required = True
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['empleado'].required = False
        form.fields['titulo'].required = True
        form.fields['descripcion'].required = True
        form.fields['sucursal'].required = True
        form.fields['fecha_hora'].required = True
        form.fields['fecha_hora'].widget.attrs.update({
            'type': 'datetime-local',
            'class': 'form-control form-control-sm',
        })
        return form

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def form_valid(self, form):
        from .validators import validate_image_file, validate_video_file, convert_video_to_h264, get_video_info_ffprobe, needs_conversion

        self.object = form.save()
        informe = self.object

        # Validar y subir imágenes
        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            try:
                validate_image_file(img)
                id_formateado = str(informe.id).zfill(10)
                numero_imagen = str(index).zfill(3)
                extension = os.path.splitext(img.name)[1].lower() or ".jpg"
                nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

                foto = FotoInforme(informe=informe)
                foto.imagen.save(nombre_archivo, ContentFile(img.read()))
                foto.save()
            except Exception as e:
                logger.error(f"Error validando imagen {img.name}: {e}")
                messages.warning(self.request, f"Imagen {img.name} no válida: {str(e)}")

        # Validar, subir y convertir videos
        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            try:
                validate_video_file(vid, validate_codec=False)
                id_formateado = str(informe.id).zfill(10)
                numero_video = str(index).zfill(3)
                nombre_archivo = f"V{id_formateado}{numero_video}.mp4"

                video = VideoInforme(informe=informe)
                video.video.save(nombre_archivo, ContentFile(vid.read()))
                video.save()

                # Verificar si necesita conversión
                video_path = video.video.path
                video_info = get_video_info_ffprobe(video_path)
                if video_info and needs_conversion(video_info):
                    logger.info(f"Convirtiendo video {vid.name} de {video_info.get('video_codec')} a H.264")
                    success = convert_video_to_h264(video_path)
                    if success:
                        logger.info(f"Video {vid.name} convertido exitosamente")
                    else:
                        logger.warning(f"No se pudo convertir el video {vid.name}")
            except Exception as e:
                logger.error(f"Error procesando video {vid.name}: {e}")
                messages.warning(self.request, f"Video {vid.name} no válido: {str(e)}")

        return super().form_valid(form)

class InformeListViewTaller(InformeFilterMixin, ListView):
    model = Informe
    template_name = 'informes/lista_taller.html'
    context_object_name = 'informes'
    paginate_by = 10

    def get_queryset(self):
        from .models import Origen

        # InformeFilterMixin ya aplica filtrado por sucursal y filtros comunes
        queryset = super().get_queryset()

        # Filtros específicos de Taller
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')

        if ficha:
            try:
                ficha = int(ficha)
                queryset = queryset.filter(bus__ficha=ficha)
            except ValueError:
                pass

        if legajo:
            try:
                legajo = int(legajo)
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass

        # Filtrar por origen Taller usando el modelo Origen
        try:
            origen_taller = Origen.objects.get(nombre='Taller')
            queryset = queryset.filter(origen=origen_taller)
        except Origen.DoesNotExist:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filtrar sucursales según permisos del usuario
        if hasattr(self.request.user, 'profile'):
            context['sucursales'] = self.request.user.profile.get_sucursales_permitidas()
        else:
            context['sucursales'] = Sucursales.objects.none()

        return context

class InformeListViewSiniestro(InformeFilterMixin, ListView):
    model = Informe
    template_name = 'informes/lista_siniestros.html'
    context_object_name = 'informes'
    paginate_by = 10

    def get_queryset(self):
        from .models import Origen

        # InformeFilterMixin ya aplica filtrado por sucursal y filtros comunes
        queryset = super().get_queryset()

        # Filtros específicos de Siniestros
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')

        if ficha:
            try:
                ficha = int(ficha)
                queryset = queryset.filter(bus__ficha=ficha)
            except ValueError:
                pass

        if legajo:
            try:
                legajo = int(legajo)
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass

        # Filtrar por origen Siniestros usando el modelo Origen
        try:
            origen_siniestros = Origen.objects.get(nombre='Siniestros')
            queryset = queryset.filter(origen=origen_siniestros)
        except Origen.DoesNotExist:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filtrar sucursales según permisos del usuario
        if hasattr(self.request.user, 'profile'):
            context['sucursales'] = self.request.user.profile.get_sucursales_permitidas()
        else:
            context['sucursales'] = Sucursales.objects.none()

        return context

class InformeListViewGuardia(InformeFilterMixin, ListView):
    model = Informe
    template_name = 'informes/lista_guardia.html'
    context_object_name = 'informes'
    paginate_by = 10

    def get_queryset(self):
        from .models import Origen

        # InformeFilterMixin ya aplica filtrado por sucursal y filtros comunes
        queryset = super().get_queryset()

        # Filtros específicos de Guardia
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')

        if ficha:
            try:
                ficha = int(ficha)
                queryset = queryset.filter(bus__ficha=ficha)
            except ValueError:
                pass

        if legajo:
            try:
                legajo = int(legajo)
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass

        # Filtrar por origen Guardia usando el modelo Origen
        try:
            origen_guardia = Origen.objects.get(nombre='Guardia')
            queryset = queryset.filter(origen=origen_guardia)
        except Origen.DoesNotExist:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filtrar sucursales según permisos del usuario
        if hasattr(self.request.user, 'profile'):
            context['sucursales'] = self.request.user.profile.get_sucursales_permitidas()
        else:
            context['sucursales'] = Sucursales.objects.none()

        return context

class InformeListView(InformeFilterMixin, ListView):
    model = Informe
    template_name = 'informes/lista_informes.html'
    context_object_name = 'informes'
    paginate_by = 10  # Paginación de 10 informes por página

    def get_queryset(self):
        # InformeFilterMixin ya aplica filtrado por sucursal y filtros comunes (titulo, fecha, origen)
        queryset = super().get_queryset()

        # Filtros adicionales
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')

        if ficha:
            try:
                ficha = int(ficha)
                queryset = queryset.filter(bus__ficha=ficha)
            except ValueError:
                pass

        if legajo:
            try:
                legajo = int(legajo)
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filtrar sucursales según permisos del usuario
        if hasattr(self.request.user, 'profile'):
            context['sucursales'] = self.request.user.profile.get_sucursales_permitidas()
            context['origenes'] = self.request.user.profile.get_origenes_permitidos()
        else:
            context['sucursales'] = Sucursales.objects.none()
            from .models import Origen
            context['origenes'] = Origen.objects.filter(activo=True)

        return context

class InformeCreateView(SucursalFormMixin, CreateView):
    model = Informe
    form_class = InformeForm
    template_name = 'informes/crear_informe.html'
    success_url = reverse_lazy('informes:lista_informes')

class InformeUpdateView(SucursalAccessMixin, UpdateView):
    model = Informe
    form_class = InformeForm
    template_name = 'informes/editar_informe.html'
    success_url = reverse_lazy('informes:lista_informes')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        return next_url or super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '')
        return context

@login_required
def lista_informes(request):
    informes = Informe.objects.all().order_by('-fecha_hora')
    print(informes)
    return render(request, 'informes/lista_informes.html', {'informes': informes})

@login_required
def buscar_informes(request):
    informes = Informe.objects.all().order_by('-fecha_hora')

    # Rango por defecto: ayer 00:00 a ahora
    default_desde = timezone.now() - timedelta(days=1)
    default_desde = default_desde.replace(hour=0, minute=0, second=0, microsecond=0)
    default_hasta = timezone.now()

    # Obtener orígenes permitidos para el usuario
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        origenes_permitidos = request.user.profile.get_origenes_permitidos()
    else:
        from .models import Origen
        origenes_permitidos = Origen.objects.filter(activo=True)

    # Pasar usuario al formulario para filtrar orígenes
    form = InformeFiltroForm(request.GET or None, user=request.user)

    # Inicializar fechas por defecto
    fecha_desde = default_desde
    fecha_hasta = default_hasta

    if form.is_valid():
        # Fechas
        fecha_desde = form.cleaned_data.get('fecha_desde') or default_desde
        fecha_hasta = form.cleaned_data.get('fecha_hasta') or default_hasta
        informes = informes.filter(fecha_hora__range=(fecha_desde, fecha_hasta))

        # Título
        filtro = form.cleaned_data.get('filtro')
        if filtro:
            informes = informes.filter(titulo__icontains=filtro)

        # Sucursal
        sucursal = form.cleaned_data.get('sucursal')
        if sucursal:
            informes = informes.filter(sucursal=sucursal)

        # Origen
        origen = form.cleaned_data.get('origen')
        if origen:
            informes = informes.filter(origen=origen)

        # Legajo del empleado 🔽
        legajo = form.cleaned_data.get('legajo')
        if legajo:
            try:
                legajo = int(legajo)  # Esto lo convierte a entero, en caso de ser un número
            except ValueError:
                pass  # Si no es numérico, dejamos el valor como cadena
            informes = informes.filter(empleado__legajo=legajo)

    else:
        informes = informes.filter(fecha_hora__range=(default_desde, default_hasta))

    # Paginación
    paginator = Paginator(informes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'page_obj': page_obj,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'sucursales': Sucursales.objects.all(),
        'origenes': origenes_permitidos,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'informes/lista_informes.html', context)

@login_required
@check_sucursal_access
@audit_file_access(action='upload_photo')
def cargar_fotos(request, pk):
    informe = get_object_or_404(Informe, pk=pk)
    fotos = FotoInforme.objects.filter(informe=informe)

    if request.method == 'POST':
        form = FotoInformeForm(request.POST, request.FILES)
        if form.is_valid():
            imagen = form.save(commit=False)
            imagen.informe = informe

            archivo = form.cleaned_data['imagen']

            # Calcular número de imagen
            cantidad_actual = fotos.count() + 1
            id_formateado = str(informe.id).zfill(10)
            numero_imagen = str(cantidad_actual).zfill(3)
            extension = os.path.splitext(archivo.name)[1] or ".jpg"
            nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

            # Guardar la imagen con el nuevo nombre
            imagen.imagen.save(nombre_archivo, ContentFile(archivo.read()))
            imagen.save()

            form = FotoInformeForm()  # Limpiar formulario

    else:
        form = FotoInformeForm()

    return render(request, 'informes/cargar_fotos.html', {
        'informe': informe,
        'form': form,
        'fotos': fotos
    })

@login_required
@check_sucursal_access
@audit_file_access(action='upload_video')
def cargar_video(request, pk):
    from .validators import convert_video_to_h264, get_video_info_ffprobe, needs_conversion

    informe = get_object_or_404(Informe, pk=pk)
    videos = VideoInforme.objects.filter(informe=informe)
    conversion_message = None

    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.informe = informe

            archivo = form.cleaned_data['video']
            if archivo.size > settings.MAX_VIDEO_UPLOAD_SIZE_MB * 1024 * 1024:
                form.add_error('video', 'El archivo excede el tamaño máximo permitido de 60MB.')
            else:
                cantidad_actual = videos.count() + 1
                id_formateado = str(informe.id).zfill(10)
                numero_video = str(cantidad_actual).zfill(3)
                # Siempre guardar como .mp4 (será convertido si es necesario)
                nombre_archivo = f"V{id_formateado}{numero_video}.mp4"
                video.video.save(nombre_archivo, ContentFile(archivo.read()))
                video.save()

                # Obtener la ruta completa del archivo guardado
                video_path = video.video.path

                # Verificar si necesita conversión
                video_info = get_video_info_ffprobe(video_path)
                if video_info and needs_conversion(video_info):
                    logger.info(f"Video requiere conversión: {video_info.get('video_codec')} → H.264")

                    # Convertir a H.264
                    result = convert_video_to_h264(video_path)

                    if result['success'] and result.get('converted'):
                        conversion_message = f"Video convertido de {result['original_codec'].upper()} a H.264 para compatibilidad web."
                        logger.info(conversion_message)

                        # Si la ruta cambió, actualizar el modelo
                        if result['output_path'] != video_path:
                            new_relative_path = os.path.relpath(result['output_path'], settings.MEDIA_ROOT)
                            video.video.name = new_relative_path
                            video.save()
                    elif not result['success']:
                        logger.error(f"Error en conversión: {result['message']}")
                        conversion_message = f"Advertencia: {result['message']}. El video puede no reproducirse en todos los navegadores."

                messages.success(request, conversion_message or "Video subido correctamente.")
            return redirect('informes:cargar_video', pk=informe.pk)
    else:
        form = VideoForm()

    return render(request, 'informes/cargar_video.html', {
        'form': form,
        'informe': informe,
        'videos': videos,
        'max_video_size_mb': settings.MAX_VIDEO_UPLOAD_SIZE_MB,
    })


@login_required
def eliminar_video(request, video_id):
    """Elimina un video físicamente y de la base de datos."""
    video = get_object_or_404(VideoInforme, id=video_id)
    informe_pk = video.informe.pk

    # Verificar acceso a la sucursal
    if hasattr(request.user, 'profile'):
        if not request.user.profile.tiene_acceso_sucursal(video.informe.sucursal):
            messages.error(request, "No tiene permiso para eliminar este video.")
            return redirect('informes:cargar_video', pk=informe_pk)

    if request.method == 'POST':
        try:
            # Eliminar archivo físico
            if video.video and hasattr(video.video, 'path'):
                video_path = video.video.path
                if os.path.exists(video_path):
                    os.remove(video_path)
                    logger.info(f"Video eliminado físicamente: {video_path}")

            # Eliminar registro de BD
            video.delete()
            messages.success(request, "Video eliminado correctamente.")
            logger.info(f"Video {video_id} eliminado por usuario {request.user.username}")

        except Exception as e:
            logger.error(f"Error eliminando video {video_id}: {e}")
            messages.error(request, f"Error al eliminar el video: {str(e)}")

    return redirect('informes:cargar_video', pk=informe_pk)


@login_required
def stream_video(request, video_id):
    """Sirve videos con soporte para Range Requests (seek)."""
    from django.http import StreamingHttpResponse, FileResponse
    import re

    video = get_object_or_404(VideoInforme, id=video_id)

    # Verificar acceso a la sucursal
    if hasattr(request.user, 'profile'):
        if not request.user.profile.tiene_acceso_sucursal(video.informe.sucursal):
            return HttpResponse("No autorizado", status=403)

    video_path = video.video.path
    if not os.path.exists(video_path):
        return HttpResponse("Video no encontrado", status=404)

    file_size = os.path.getsize(video_path)
    content_type = 'video/mp4'

    # Manejar Range Request para seek
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)

    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1

        def file_iterator():
            with open(video_path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        response = StreamingHttpResponse(file_iterator(), status=206, content_type=content_type)
        response['Content-Length'] = length
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    else:
        # Sin Range, enviar archivo completo
        response = FileResponse(open(video_path, 'rb'), content_type=content_type)
        response['Content-Length'] = file_size

    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = f'inline; filename="{os.path.basename(video_path)}"'
    return response


@login_required
@check_sucursal_access
@audit_file_access(action='view_photo')
def ver_foto(request, foto_id):
    foto = get_object_or_404(FotoInforme, id=foto_id)
    informe = foto.informe
    fotos = list(informe.fotos.all().order_by('id'))
    
    actual_index = fotos.index(foto)
    anterior = fotos[actual_index - 1].id if actual_index > 0 else fotos[-1].id
    siguiente = fotos[actual_index + 1].id if actual_index < len(fotos) - 1 else fotos[0].id

    contexto = {
        'foto': foto,
        'informe': informe,
        'anterior_id': anterior,
        'siguiente_id': siguiente
    }
    return render(request, 'informes/ver_foto.html', contexto)

@login_required
def informes_sin_legajo(request, sucursal_id=None):
    """Vista para mostrar informes sin empleado asignado, filtrados por sucursal."""
    # Obtener sucursales permitidas para el usuario
    if hasattr(request.user, 'profile'):
        sucursales = request.user.profile.get_sucursales_permitidas()
    else:
        sucursales = Sucursales.objects.none()

    # Si no hay sucursal_id, verificar si tiene solo una sucursal
    if sucursal_id is None:
        if sucursales.count() == 1:
            # Redirigir directamente a la única sucursal
            return redirect('informes:informes_sin_legajo_sucursal', sucursal_id=sucursales.first().id)
        # Mostrar selección de sucursal
        return render(request, 'informes/seleccionar_sucursal_sin_legajo.html', {
            'sucursales': sucursales
        })

    # Verificar acceso a la sucursal
    sucursal = get_object_or_404(Sucursales, id=sucursal_id)
    if hasattr(request.user, 'profile'):
        if not request.user.profile.tiene_acceso_sucursal(sucursal):
            messages.error(request, 'No tiene permisos para ver informes de esta sucursal.')
            return redirect('informes:informes_sin_legajo')

    # Filtrar informes sin empleado de la sucursal seleccionada
    informes = Informe.objects.filter(
        empleado__isnull=True,
        sucursal=sucursal
    ).select_related('bus', 'sucursal', 'origen').prefetch_related('fotos', 'videos').order_by('-fecha_hora')

    return render(request, 'informes/sin_legajo.html', {
        'informes': informes,
        'sucursal': sucursal,
        'sucursales': sucursales
    })

class EnviarInformeEmailView(LoginRequiredMixin, FormView):
    template_name = 'informes/enviar_email.html'
    form_class = EnviarInformeEmailForm

    def dispatch(self, request, *args, **kwargs):
        self.informe = get_object_or_404(
            Informe.objects.select_related('bus', 'sucursal', 'empleado', 'origen'),
            pk=kwargs['pk']
        )
        self.next_url = request.GET.get('next')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        correos_raw = form.cleaned_data['destinatarios']
        correos = [c.strip() for c in correos_raw.split(",") if c.strip()]
        ultimos_informes = Informe.objects.filter(empleado=self.informe.empleado).exclude(id=self.informe.id).order_by('-fecha_hora')[:10]

        try:
            enviar_informe_por_mail(self.informe, correos, ultimos_informes=list(ultimos_informes))
            messages.success(self.request, "Correo enviado correctamente.")
        except Exception as e:
            messages.error(self.request, f"Ocurrió un error al enviar el correo: {e}")

        if self.next_url and url_has_allowed_host_and_scheme(self.next_url, allowed_hosts=None):
            return redirect(self.next_url)

        return redirect('informes:lista_informes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['informe'] = self.informe
        context['next'] = self.next_url  
        return context

@login_required
def informes_no_enviados(request):
    informes_no_enviados = Informe.objects.filter(historial_envios__isnull=True)

    if request.method == "POST":
        informes_ids = request.POST.getlist("informes_ids")

        if informes_ids:
            for informe_id in informes_ids:
                informe = Informe.objects.get(id=informe_id)
                destinatarios = informe.sucursal.obtener_destinatarios()
                
                try:
                    enviar_informe_por_mail(informe, destinatarios)
                    messages.success(request, f"Informe {informe.id} enviado correctamente.")
                except Exception as e:
                    messages.error(request, f"Error al enviar el informe {informe.id}: {str(e)}")

            return redirect("informes:informes_no_enviados")  

    return render(request, "informes/informes_no_enviados.html", {
        "informes_no_enviados": informes_no_enviados,
    })

@login_required
def informes_asociar_sitinforme(request):
    if request.method == 'POST':
        ids = request.POST.getlist('informes_ids')
        if ids:
            for id_str in ids:
                try:
                    informe = Informe.objects.get(id=id_str)
                    informe.generado = True
                    informe.save()

                    nro_expediente = request.POST.get(f'nro_expediente_{id_str}')
                    if nro_expediente:
                        expediente, created = ExpedienteInforme.objects.get_or_create(
                            informe=informe,
                            defaults={'nro_expediente': int(nro_expediente),
                                      'tipo': 'I' }
                        )
                        if not created:
                            expediente.nro_expediente = int(nro_expediente)
                            expediente.tipo = 'I'                            
                            expediente.save()
                except Informe.DoesNotExist:
                    continue

            messages.success(request, f'Se marcaron {len(ids)} informes como generados y se guardaron los expedientes.')
        else:
            messages.warning(request, 'No seleccionaste ningún informe.')

        return redirect('informes:sit_informe')

    informes_no_generados = Informe.objects.filter(generado=False).select_related('sucursal', 'bus', 'empleado').prefetch_related('fotos')
    return render(request, 'informes/sit_asociarinforme.html', { 'informes_no_generados': informes_no_generados })

@login_required
def informes_asociar_sitsiniestro(request):
    if request.method == 'POST':
        ids = request.POST.getlist('informes_ids')
        if ids:
            for id_str in ids:
                try:
                    informe = Informe.objects.get(id=id_str)
                    informe.generado = True
                    informe.save()

                    nro_expediente = request.POST.get(f'nro_expediente_{id_str}')
                    if nro_expediente:
                        expediente, created = ExpedienteInforme.objects.get_or_create(
                            informe=informe,
                            defaults={'nro_expediente': int(nro_expediente),
                                      'tipo': 'S' }
                        )
                        if not created:
                            expediente.nro_expediente = int(nro_expediente)
                            expediente.tipo = 'S'                            
                            expediente.save()
                except Informe.DoesNotExist:
                    continue

            messages.success(request, f'Se marcaron {len(ids)} informes como generados y se guardaron los expedientes.')
        else:
            messages.warning(request, 'No seleccionaste ningún informe.')

        return redirect('informes:sit_siniestro')

    informes_no_generados = Informe.objects.filter(generado=False).select_related('sucursal', 'bus', 'empleado').prefetch_related('fotos')
    return render(request, 'informes/sit_asociarsiniestro.html', { 'informes_no_generados': informes_no_generados })

@login_required
def informes_desestimar(request):
    if request.method == 'POST':
        ids = request.POST.getlist('informes_ids')
        if ids:
            for id_str in ids:
                comentario = request.POST.get(f'comentario_{id_str}', '').strip()

                if not comentario:
                    messages.warning(request, f'Falta comentario para desestimar el informe Nº {id_str}.')
                    continue

                try:
                    informe = Informe.objects.get(id=id_str)
                    informe.generado = True
                    informe.save()

                    expediente, created = ExpedienteInforme.objects.get_or_create(
                        informe=informe,
                        defaults={
                            'nro_expediente': 0,
                            'tipo': 'D',
                            'comentario': comentario
                        }
                    )
                    if not created:
                        expediente.nro_expediente = 0
                        expediente.tipo = 'D'
                        expediente.comentario = comentario
                        expediente.save()

                except Informe.DoesNotExist:
                   continue

            messages.success(request, f'Se desestimaron {len(ids)} informes con sus comentarios correspondientes.')
        else:
            messages.warning(request, 'No seleccionaste ningún informe.')

        return redirect('informes:desestimar')

    desestimar = Informe.objects.filter(generado=False).select_related('sucursal', 'bus', 'empleado').prefetch_related('fotos')
    return render(request, 'informes/desestimar.html', { 'desestimar': desestimar })

class InformesPorEmpleadoView(LoginRequiredMixin, View):
    def get(self, request):
        empleado_id = request.GET.get('empleado')
        informes = []
        empleado = None

        if empleado_id:
            empleado = get_object_or_404(Empleado, id=empleado_id)
            informes = Informe.objects.filter(empleado=empleado).order_by('-fecha_hora').prefetch_related('fotos', 'videos')

        empleados = Empleado.objects.order_by('apellido', 'nombre')
        return render(request, 'informes/informes_por_empleado.html', {
            'informes': informes,
            'empleado': empleado,
            'empleados': empleados,
        })

class InformeBorrarView(LoginRequiredMixin, View):
    template_name = 'informes/borrar_informe.html'
    success_url = reverse_lazy('informes:lista_informes')

    def get(self, request, pk):
        informe = get_object_or_404(Informe, pk=pk)
        context = {'informe': informe}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        informe = get_object_or_404(Informe, pk=pk)
        informe.delete()
        messages.success(request, f'El informe con ID {pk} ha sido borrado correctamente.')
        return redirect(self.success_url)

@login_required
def estadisticas_informes(request):

    anio_actual = datetime.now().year
    anio = int(request.GET.get('anio', anio_actual))
    mes = int(request.GET.get('mes')) if request.GET.get('mes') else None
    sucursal_id = int(request.GET.get('sucursal')) if request.GET.get('sucursal') else None

    informes = Informe.objects.filter(fecha_hora__year=anio)
    if mes:
        informes = informes.filter(fecha_hora__month=mes)
    if sucursal_id:
        informes = informes.filter(sucursal_id=sucursal_id)

    origenes = informes.values('origen').annotate(total=Count('id')).order_by('-total')
    labels = [o['origen'] for o in origenes]
    datos = [o['total'] for o in origenes]

    ranking_buses = (
        informes.values('bus__ficha')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    ranking_buses = [(rb['bus__ficha'], rb['total']) for rb in ranking_buses]

    ranking_choferes = (
        informes.values('empleado__apellido', 'empleado__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    ranking_choferes = [
        (f"{rc['empleado__apellido']}, {rc['empleado__nombre']}", rc['total'])
        for rc in ranking_choferes
    ]


    context = {
        'anios': list(range(anio_actual, anio_actual - 10, -1)),
        'anio': anio,
        'mes': mes,
        'meses': [(i, month_name[i].capitalize()) for i in range(1, 13)],
        'sucursales': Sucursales.objects.all(),
        'sucursal_id': sucursal_id,
        'labels': json.dumps(labels),
        'datos': json.dumps(datos),
        'ranking_buses': ranking_buses,
        'ranking_choferes': ranking_choferes,
    }

    return render(request, 'informes/dashboard.html', context)

@login_required
def informes_disciplinarios(request):
    informes = Informe.objects.filter(expediente__isnull=False).select_related('bus', 'empleado', 'expediente').prefetch_related('fotos')
    
    # Filtros...
    mes = request.GET.get('mes')
    anio = request.GET.get('anio')
    ficha = request.GET.get('ficha')
    legajo = request.GET.get('legajo')

    if mes:
        informes = informes.filter(fecha_hora__month=mes)
    if anio:
        informes = informes.filter(fecha_hora__year=anio)
    if ficha:
        informes = informes.filter(bus__ficha__icontains=ficha)
    if legajo:
        informes = informes.filter(empleado__legajo__icontains=legajo)

    paginator = Paginator(informes, 4)  # 4 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'informes/lista_disciplinarios.html', {
        'page_obj': page_obj,
    })

@xframe_options_exempt
def descargar_expediente_pdf(request, expediente_id):
    parametros = {
        'rs:Format': 'PDF',
        'rs:Command': 'Render',
        'pBase': 1,
        'pEmpresa': 1,
        'pExpediente': expediente_id,
    }

    base_url = "http://190.183.254.254:82/ReportesSIT/ReportServer"
    full_url = f"{base_url}?%2fPersonal%2fExpedienteInforme&{urlencode(parametros)}"

    auth = HTTPBasicAuth("reporte.mail", "autobuses")
    response = requests.get(full_url, auth=auth, timeout=40)

    if response.status_code == 200:
        return HttpResponse(
            response.content,
            content_type='application/pdf',
            headers={'Content-Disposition': 'inline; filename="ExpedienteInforme.pdf"'}
        )
    else:        
        return HttpResponse(f"Error al generar PDF: {response.status_code}", status=500)
    pass

class InformeCreateInspectores(SucursalFormMixin, CreateView):
    model = Informe
    form_class = InformeForm
    template_name = 'informes/informe_inspectores.html'
    success_url = reverse_lazy('informes:lista_informes')

    def form_valid(self, form):
        form.instance.origen = 'Inspectores'
        messages.success(self.request, "✅ Informe de Inspectores creado correctamente")
        return super().form_valid(form)

class InformeListViewInspectores(InformeFilterMixin, ListView):
    model = Informe
    template_name = 'informes/lista_inspectores.html'
    context_object_name = 'informes'
    paginate_by = 10

    def get_queryset(self):
        # InformeFilterMixin ya aplica filtrado por sucursal
        queryset = super().get_queryset()
        # Filtrar por origen Inspectores
        return queryset.filter(origen='Inspectores')


@login_required
def buscar_empleados_ajax(request):
    """
    Endpoint Ajax para buscar empleados por sucursal y término de búsqueda.
    Requiere al menos 3 caracteres para activar la búsqueda.
    """
    query = request.GET.get('q', '').strip()
    sucursal_id = request.GET.get('sucursal_id', '')

    # Validar que tenga al menos 3 caracteres
    if len(query) < 3:
        return JsonResponse({'empleados': []})

    # Validar sucursal
    if not sucursal_id:
        return JsonResponse({'empleados': [], 'error': 'Debe seleccionar una sucursal primero'})

    try:
        sucursal_id = int(sucursal_id)
    except ValueError:
        return JsonResponse({'empleados': [], 'error': 'ID de sucursal inválido'})

    # Verificar permisos del usuario sobre la sucursal
    if hasattr(request.user, 'profile'):
        sucursales_permitidas = request.user.profile.get_sucursales_permitidas()
        if not sucursales_permitidas.filter(id=sucursal_id).exists():
            return JsonResponse({'empleados': [], 'error': 'No tiene permisos para esta sucursal'})

    # Buscar empleados por legajo o nombre/apellido
    empleados = Empleado.objects.filter(sucursal_id=sucursal_id)

    # Filtrar por legajo si es numérico, sino por nombre/apellido
    if query.isdigit():
        empleados = empleados.filter(legajo__icontains=query)
    else:
        empleados = empleados.filter(
            Q(nombre__icontains=query) | Q(apellido__icontains=query)
        )

    empleados = empleados.order_by('apellido', 'nombre')[:20]  # Limitar a 20 resultados

    data = {
        'empleados': [
            {
                'id': emp.id,
                'legajo': emp.legajo,
                'nombre_completo': f"{emp.apellido}, {emp.nombre}",
                'display': f"{emp.legajo} - {emp.apellido}, {emp.nombre}"
            }
            for emp in empleados
        ]
    }

    return JsonResponse(data)


@login_required
def buscar_buses_ajax(request):
    """
    Endpoint Ajax para buscar buses por término de búsqueda.
    Requiere al menos 3 caracteres para activar la búsqueda.
    Nota: Buses no están asociados a sucursales, se buscan globalmente.
    """
    query = request.GET.get('q', '').strip()

    # Validar que tenga al menos 3 caracteres
    if len(query) < 3:
        return JsonResponse({'buses': []})

    # Buscar buses por ficha (sin filtro de sucursal porque Buses no tiene ese campo)
    buses = Buses.objects.filter(
        ficha__icontains=query,
        estado=True  # Solo buses activos
    ).order_by('ficha')[:20]  # Limitar a 20 resultados

    data = {
        'buses': [
            {
                'id': bus.id,
                'ficha': str(bus.ficha),
                'dominio': bus.dominio,
                'display': f"Ficha {bus.ficha} - {bus.dominio}"
            }
            for bus in buses
        ]
    }

    return JsonResponse(data)

