from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count
from django.urls import reverse_lazy
from django.utils import timezone
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
from django.http import HttpResponse

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

class ListaInformesBorrarView(View):
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

class InformeCreateSistemas(CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_sistemas.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        return {'origen': 'Sistemas',
                'fecha_hora': timezone.now(),}
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.all().order_by('ficha')
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['fecha_hora'].widget.attrs.update({'type': 'datetime-local','class': 'form-control form-control-sm',})
        return form
    
    def form_valid(self, form):
        self.object = form.save()
        form.instance.origen = 'Sistemas'
        informe = self.object

        # Subir imágenes renombradas
        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_imagen = str(index).zfill(3)
            extension = os.path.splitext(img.name)[1] or ".jpg"
            nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

            foto = FotoInforme(informe=informe)
            foto.imagen.save(nombre_archivo, ContentFile(img.read()))
            foto.save()

        # Subir videos renombrados
        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_video = str(index).zfill(3)
            extension = os.path.splitext(vid.name)[1] or ".mp4"
            nombre_archivo = f"V{id_formateado}{numero_video}{extension}"

            video = VideoInforme(informe=informe)
            video.video.save(nombre_archivo, ContentFile(vid.read()))
            video.save()

        return super().form_valid(form)

class InformeCreateGuardia(CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_guardia.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        return {'origen': 'Guardia',
                'fecha_hora': timezone.now(),}
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.all().order_by('ficha')
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['fecha_hora'].widget.attrs.update({'type': 'datetime-local','class': 'form-control form-control-sm',})
        return form
    
    def form_valid(self, form):
        self.object = form.save()
        form.instance.origen = 'Guardia'
        informe = self.object

        # Subir imágenes renombradas
        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_imagen = str(index).zfill(3)
            extension = os.path.splitext(img.name)[1] or ".jpg"
            nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

            foto = FotoInforme(informe=informe)
            foto.imagen.save(nombre_archivo, ContentFile(img.read()))
            foto.save()

        # Subir videos renombrados
        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_video = str(index).zfill(3)
            extension = os.path.splitext(vid.name)[1] or ".mp4"
            nombre_archivo = f"V{id_formateado}{numero_video}{extension}"

            video = VideoInforme(informe=informe)
            video.video.save(nombre_archivo, ContentFile(vid.read()))
            video.save()

        return super().form_valid(form)

class InformeCreateSiniestros(CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_siniestro.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        return {'origen': 'Siniestros',
                'fecha_hora': timezone.now(),}
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.all().order_by('ficha')
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['fecha_hora'].widget.attrs.update({'type': 'datetime-local','class': 'form-control form-control-sm',})
        return form
    
    def form_valid(self, form):
        self.object = form.save()
        form.instance.origen = 'Siniestro'
        informe = self.object

        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_imagen = str(index).zfill(3)
            extension = os.path.splitext(img.name)[1] or ".jpg"
            nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

            foto = FotoInforme(informe=informe)
            foto.imagen.save(nombre_archivo, ContentFile(img.read()))
            foto.save()

        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_video = str(index).zfill(3)
            extension = os.path.splitext(vid.name)[1] or ".mp4"
            nombre_archivo = f"V{id_formateado}{numero_video}{extension}"

            video = VideoInforme(informe=informe)
            video.video.save(nombre_archivo, ContentFile(vid.read()))
            video.save()

        return super().form_valid(form)

class InformeCreateTaller(CreateView):
    model = Informe
    form_class = InformeGuardia
    template_name = "informes/informe_taller.html"
    success_url = reverse_lazy("inicio")

    def get_initial(self):
        return {'origen': 'Taller',
                'fecha_hora': timezone.now(),}
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['bus'].queryset = Buses.objects.all().order_by('ficha')
        form.fields['empleado'].queryset = Empleado.objects.all().order_by('apellido')
        form.fields['fecha_hora'].widget.attrs.update({'type': 'datetime-local','class': 'form-control form-control-sm',})
        return form
    
    def form_valid(self, form):
        self.object = form.save()
        form.instance.origen = 'Taller'
        informe = self.object

        for index, img in enumerate(self.request.FILES.getlist("imagenes"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_imagen = str(index).zfill(3)
            extension = os.path.splitext(img.name)[1] or ".jpg"
            nombre_archivo = f"F{id_formateado}{numero_imagen}{extension}"

            foto = FotoInforme(informe=informe)
            foto.imagen.save(nombre_archivo, ContentFile(img.read()))
            foto.save()

        for index, vid in enumerate(self.request.FILES.getlist("videos"), start=1):
            id_formateado = str(informe.id).zfill(10)
            numero_video = str(index).zfill(3)
            extension = os.path.splitext(vid.name)[1] or ".mp4"
            nombre_archivo = f"V{id_formateado}{numero_video}{extension}"

            video = VideoInforme(informe=informe)
            video.video.save(nombre_archivo, ContentFile(vid.read()))
            video.save()

        return super().form_valid(form)

class InformeListViewTaller(ListView):
    model = Informe
    template_name = 'informes/lista_taller.html'
    context_object_name = 'informes'
    paginate_by = 10  

    def get_queryset(self):
        queryset = super().get_queryset().select_related('bus', 'sucursal', 'empleado')

        filtro = self.request.GET.get('filtro', '')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        sucursal = self.request.GET.get('sucursal')
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')
        origen_fil = self.request.GET.get('origen')

        if ficha:
            try:
                ficha = int(ficha)  
                queryset = queryset.filter(bus__ficha=ficha)  
            except ValueError:
                pass  

        if filtro:
            queryset = queryset.filter(titulo__icontains=filtro)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)

        if sucursal:
            queryset = queryset.filter(sucursal_id=sucursal)
        
        queryset = queryset.filter(origen='Taller')

        if legajo:
            try:
                legajo = int(legajo) 
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass  
        return queryset.order_by('-fecha_hora')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sucursales'] = Sucursales.objects.all()  
        return context

class InformeListViewSiniestro(ListView):
    model = Informe
    template_name = 'informes/lista_siniestros.html'
    context_object_name = 'informes'
    paginate_by = 10  

    def get_queryset(self):
        queryset = super().get_queryset().select_related('bus', 'sucursal', 'empleado')

        filtro = self.request.GET.get('filtro', '')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        sucursal = self.request.GET.get('sucursal')
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')
        origen_fil = self.request.GET.get('origen')

        if ficha:
            try:
                ficha = int(ficha)  
                queryset = queryset.filter(bus__ficha=ficha)  
            except ValueError:
                pass  

        if filtro:
            queryset = queryset.filter(titulo__icontains=filtro)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)

        if sucursal:
            queryset = queryset.filter(sucursal_id=sucursal)
        
        queryset = queryset.filter(origen='Siniestros')

        if legajo:
            try:
                legajo = int(legajo) 
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass  
        return queryset.order_by('-fecha_hora')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sucursales'] = Sucursales.objects.all()  
        return context

class InformeListViewGuardia(ListView):
    model = Informe
    template_name = 'informes/lista_guardia.html'
    context_object_name = 'informes'
    paginate_by = 10  

    def get_queryset(self):
        queryset = super().get_queryset().select_related('bus', 'sucursal', 'empleado')

        filtro = self.request.GET.get('filtro', '')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        sucursal = self.request.GET.get('sucursal')
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')
        origen_fil = self.request.GET.get('origen')

        if ficha:
            try:
                ficha = int(ficha)  
                queryset = queryset.filter(bus__ficha=ficha)  
            except ValueError:
                pass  

        if filtro:
            queryset = queryset.filter(titulo__icontains=filtro)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)

        if sucursal:
            queryset = queryset.filter(sucursal_id=sucursal)
        
        queryset = queryset.filter(origen='Guardia')

        if legajo:
            try:
                legajo = int(legajo) 
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass  
        return queryset.order_by('-fecha_hora')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sucursales'] = Sucursales.objects.all()  
        return context

class InformeListView(ListView):
    model = Informe
    template_name = 'informes/lista_informes.html'
    context_object_name = 'informes'
    paginate_by = 10  # Paginación de 10 informes por página

    def get_queryset(self):
        queryset = super().get_queryset().select_related('bus', 'sucursal', 'empleado')

        filtro = self.request.GET.get('filtro', '')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        sucursal = self.request.GET.get('sucursal')
        legajo = self.request.GET.get('legajo')
        ficha = self.request.GET.get('numero_ficha')
        origen_fil = self.request.GET.get('origen')

        if ficha:
            try:
                ficha = int(ficha)  # Convertir 'ficha' a entero
                queryset = queryset.filter(bus__ficha=ficha)  # Filtrar por el número de ficha
            except ValueError:
                pass  

        if filtro:
            queryset = queryset.filter(titulo__icontains=filtro)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)

        if sucursal:
            queryset = queryset.filter(sucursal_id=sucursal)
        
        if origen_fil:
            queryset = queryset.filter(origen=origen_fil)

        if legajo:
            try:
                legajo = int(legajo)  # Esto lo convierte a entero, en caso de ser un número
                queryset = queryset.filter(empleado__legajo=legajo)
            except ValueError:
                pass  # Si no es numérico, no filtra por legaj
        return queryset.order_by('-fecha_hora')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sucursales'] = Sucursales.objects.all()  
        return context

class InformeCreateView(CreateView):
    model = Informe
    form_class = InformeForm
    template_name = 'informes/crear_informe.html'
    success_url = reverse_lazy('informes:lista_informes')

class InformeUpdateView(UpdateView):
    model = Informe
    form_class = InformeForm
    template_name = 'informes/editar_informe.html'
    success_url = reverse_lazy('informes:lista_informes')

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        return next_url or super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '')
        return context

def lista_informes(request):
    informes = Informe.objects.all().order_by('-fecha_hora')
    print(informes)
    return render(request, 'informes/lista_informes.html', {'informes': informes})

def buscar_informes(request):
    informes = Informe.objects.all().order_by('-fecha_hora')

    # Rango por defecto: ayer 00:00 a ahora
    default_desde = timezone.now() - timedelta(days=1)
    default_desde = default_desde.replace(hour=0, minute=0, second=0, microsecond=0)
    default_hasta = timezone.now()

    form = InformeFiltroForm(request.GET or None)

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
    }
    return render(request, 'informes/lista_informes.html', context)

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

def cargar_video(request, pk):
    informe = get_object_or_404(Informe, pk=pk)
    videos = VideoInforme.objects.filter(informe=informe)

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
                extension = os.path.splitext(archivo.name)[1] or ".mp4"
                nombre_archivo = f"V{id_formateado}{numero_video}{extension}"            
                video.video.save(nombre_archivo, ContentFile(archivo.read()))
                video.save()

            return redirect('informes:cargar_video', pk=informe.pk)  # Evita reenviar formulario al refrescar
    else:
        form = VideoForm()

    return render(request, 'informes/cargar_video.html', {
        'form': form,
        'informe': informe,
        'videos': videos,
        'max_video_size_mb': settings.MAX_VIDEO_UPLOAD_SIZE_MB,
    })

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

def informes_sin_legajo(request):
    informes = Informe.objects.filter(empleado__isnull=True)    
    return render(request, 'informes/sin_legajo.html', {'informes': informes})

class EnviarInformeEmailView(FormView):
    template_name = 'informes/enviar_email.html'
    form_class = EnviarInformeEmailForm

    def dispatch(self, request, *args, **kwargs):
        self.informe = get_object_or_404(Informe, pk=kwargs['pk'])
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

class InformesPorEmpleadoView(View):
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

class InformeBorrarView(View):
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

class InformeCreateInspectores(CreateView):
    model = Informe
    form_class = InformeForm
    template_name = 'informes/informe_inspectores.html'
    success_url = reverse_lazy('informes:lista_informes')
    
    def form_valid(self, form):
        form.instance.origen = 'Inspectores'
        messages.success(self.request, "✅ Informe de Inspectores creado correctamente")
        return super().form_valid(form)

class InformeListViewInspectores(ListView):
    model = Informe
    template_name = 'informes/lista_inspectores.html'
    context_object_name = 'informes'
    paginate_by = 10
    
    def get_queryset(self):
        return Informe.objects.filter(origen='Inspectores').order_by('-fecha_hora')



