from django import forms
from django.utils.timezone import localtime
from .models import Informe, FotoInforme, VideoInforme, Sucursales, Empleado, Buses
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .validators import validate_image_file, validate_video_file, get_video_codec_info

class InformeGuardia(forms.ModelForm):
    class Meta:
        model = Informe
        fields = ['titulo', 'descripcion', 'sucursal', 'bus', 'empleado', 'origen','fecha_hora']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'sucursal': forms.Select(attrs={'class': 'form-control'}),
            'bus': forms.Select(attrs={'class': 'form-control'}),
            'empleado': forms.Select(attrs={'class': 'form-control'}),
            'origen': forms.Select(attrs={'class': 'form-control'}),
            'fecha_hora': forms.DateTimeInput(attrs={'type': 'datetime-local','class': 'form-control form-control-sm',}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filtrar sucursales y orígenes según permisos del usuario
        if user and hasattr(user, 'profile'):
            self.fields['sucursal'].queryset = user.profile.get_sucursales_permitidas()

            # Filtrar orígenes según permisos del usuario
            origenes_permitidos = user.profile.get_origenes_permitidos()
            self.fields['origen'].queryset = origenes_permitidos

            # Intentar establecer 'Guardia' como predeterminado si está permitido
            try:
                guardia = origenes_permitidos.get(nombre='Guardia')
                self.fields['origen'].initial = guardia.id
            except:
                # Si no existe 'Guardia' o no está permitido, usar el primero disponible
                if origenes_permitidos.exists():
                    self.fields['origen'].initial = origenes_permitidos.first().id

class InformeForm(forms.ModelForm):
    # Campos personalizados para autocompletado Ajax
    empleado_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escriba al menos 3 caracteres del legajo o nombre...',
            'autocomplete': 'off'
        }),
        label='Buscar Empleado'
    )

    bus_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escriba al menos 3 caracteres de la ficha...',
            'autocomplete': 'off'
        }),
        label='Buscar Bus'
    )

    class Meta:
        model = Informe
        fields = ['titulo', 'descripcion', 'sucursal','empleado','bus', 'fecha_hora', 'origen']
        widgets = {
            'fecha_hora': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del informe'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Descripción detallada del informe...'
            }),
            'sucursal': forms.Select(attrs={'class': 'form-select'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Configurar campos empleado y bus como hidden (serán manejados por Ajax)
        self.fields['empleado'].required = False
        self.fields['empleado'].widget = forms.HiddenInput()
        self.fields['bus'].required = True  # Bus obligatorio
        self.fields['bus'].widget = forms.HiddenInput()

        # Fecha y hora obligatoria
        self.fields['fecha_hora'].required = True

        # Filtrar sucursales y orígenes según permisos del usuario
        if user and hasattr(user, 'profile'):
            self.fields['sucursal'].queryset = user.profile.get_sucursales_permitidas()
            self.fields['origen'].queryset = user.profile.get_origenes_permitidos()

        # Si es edición, cargar los valores actuales en los campos de búsqueda
        if self.instance and self.instance.pk:
            if self.instance.empleado:
                self.fields['empleado_search'].initial = f"{self.instance.empleado.legajo} - {self.instance.empleado.apellido}, {self.instance.empleado.nombre}"
            if self.instance.bus:
                self.fields['bus_search'].initial = f"Ficha {self.instance.bus.ficha}"

            if self.instance.fecha_hora:
                local_dt = localtime(self.instance.fecha_hora)
                self.initial['fecha_hora'] = local_dt.strftime('%Y-%m-%dT%H:%M')

            # En edición, hacer sucursal y bus readonly
            self.fields['sucursal'].widget.attrs['disabled'] = 'disabled'
            self.fields['sucursal'].required = False  # Disabled fields don't submit, so make it not required
            self.fields['bus_search'].widget.attrs['readonly'] = 'readonly'
            self.fields['bus_search'].widget.attrs['disabled'] = 'disabled'

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Si es edición y sucursal no viene en los datos (porque está disabled),
        # preservar el valor original
        if self.instance.pk and not self.cleaned_data.get('sucursal'):
            # Recargar el objeto original para obtener la sucursal
            original = Informe.objects.get(pk=self.instance.pk)
            instance.sucursal = original.sucursal

        if commit:
            instance.save()
        return instance

class InformeFiltroForm(forms.Form):
    filtro = forms.CharField(required=False, label='Título')
    fecha_desde = forms.DateTimeField(required=False,widget=forms.DateTimeInput(attrs={'type': 'datetime-local','class': 'form-control'}))
    fecha_hasta = forms.DateTimeField(required=False,widget=forms.DateTimeInput(attrs={'type': 'datetime-local','class': 'form-control'}))
    sucursal = forms.ModelChoiceField(queryset=Sucursales.objects.all(), required=False)
    origen = forms.ModelChoiceField(queryset=None, required=False, label="Origen")
    legajo = forms.IntegerField(required=False, label="Legajo")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filtrar orígenes según permisos del usuario
        from .models import Origen
        if user and hasattr(user, 'profile'):
            self.fields['origen'].queryset = user.profile.get_origenes_permitidos()
        else:
            self.fields['origen'].queryset = Origen.objects.filter(activo=True)    

class FotoInformeForm(forms.ModelForm):
    class Meta:
        model = FotoInforme
        fields = ['imagen']
        widgets = { 'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),}

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            # Validación robusta: MIME type + contenido real del archivo
            try:
                validate_image_file(imagen)
            except ValidationError as e:
                raise forms.ValidationError(str(e.message if hasattr(e, 'message') else e))
        return imagen        
    
class VideoForm(forms.ModelForm):
    """
    Formulario para subida de videos con validación de:
    - Tamaño máximo (configurable en settings.MAX_VIDEO_UPLOAD_SIZE_MB)
    - MIME type real del archivo
    - Codecs de video permitidos (H.264, H.265, VP9, AV1, MPEG-4)

    Si ffprobe está instalado, valida también el codec del video.
    """
    class Meta:
        model = VideoInforme
        fields = ['video']
        widgets = {
            'video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar información de formatos aceptados
        self.fields['video'].help_text = (
            "Formatos permitidos: MP4, AVI, MOV, MKV, WEBM. "
            "Codecs: H.264, H.265/HEVC, VP9, AV1"
        )

    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video:
            # Validación robusta: MIME type + codec de video
            try:
                video_info = validate_video_file(video, validate_codec=True)

                # Guardar información del codec para uso posterior
                if video_info:
                    self._video_info = video_info
                    codec = video_info.get('video_codec', '')
                    codec_info = get_video_codec_info(codec)
                    if codec_info:
                        # Log informativo del codec detectado
                        import logging
                        logger = logging.getLogger('informes.forms')
                        logger.info(
                            f"Video aceptado: {video.name}, "
                            f"codec: {codec_info['name']}, "
                            f"resolución: {video_info.get('width')}x{video_info.get('height')}"
                        )
            except ValidationError as e:
                raise forms.ValidationError(str(e.message if hasattr(e, 'message') else e))
        return video

    def get_video_info(self):
        """Retorna información del video si fue analizado con ffprobe."""
        return getattr(self, '_video_info', None)   

class EnviarInformeEmailForm(forms.Form):
    destinatarios = forms.CharField(label='Destinatarios', widget=forms.Textarea(attrs={'rows': 2}))

    def clean_destinatarios(self):
        datos = self.cleaned_data['destinatarios']
        correos = [c.strip() for c in datos.split(",")]
        for correo in correos:
            try:
                validate_email(correo)
            except ValidationError:
                raise forms.ValidationError(f"Correo inválido: {correo}")
        return datos        