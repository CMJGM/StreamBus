from django import forms
from django.utils.timezone import localtime
from .models import Informe, FotoInforme, VideoInforme, Sucursales, Empleado, Buses
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

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

class InformeFiltroForm(forms.Form):
    filtro = forms.CharField(required=False, label='Título')
    fecha_desde = forms.DateTimeField(required=False,widget=forms.DateTimeInput(attrs={'type': 'datetime-local','class': 'form-control'}))
    fecha_hasta = forms.DateTimeField(required=False,widget=forms.DateTimeInput(attrs={'type': 'datetime-local','class': 'form-control'}))
    sucursal = forms.ModelChoiceField(queryset=Sucursales.objects.all(), required=False)
    legajo = forms.IntegerField(required=False, label="Legajo")    

class FotoInformeForm(forms.ModelForm):
    class Meta:
        model = FotoInforme
        fields = ['imagen']
        widgets = { 'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),}

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            if not imagen.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise forms.ValidationError("Solo se permiten archivos .jpg, .jpeg o .png")
        return imagen        
    
class VideoForm(forms.ModelForm):
    class Meta:
        model = VideoInforme
        fields = ['video']
        widgets = {
                    'video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
                }  
    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video:
            ext = video.name.split('.')[-1].lower()
            if ext not in ['mp4', 'avi']:
                raise forms.ValidationError('Solo se permiten archivos .mp4 o .avi')
        return video   

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