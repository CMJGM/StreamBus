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
        super().__init__(*args, **kwargs)
        self.fields['origen'].initial = 'Guardia'

class InformeForm(forms.ModelForm):    

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
                'rows': 4,
                'placeholder': 'Descripción detallada del informe...'
            }),
            'sucursal': forms.Select(attrs={'class': 'form-select'}),
            'bus': forms.Select(attrs={'class': 'form-select'}),
            'empleado': forms.Select(attrs={'class': 'form-select'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
        }
   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].required = False  
        self.fields['empleado'].queryset = Empleado.objects.order_by('apellido', 'nombre')        
        self.fields['bus'].required = False  
        self.fields['bus'].queryset = Buses.objects.order_by('ficha')        

        if 'fecha_hora' in self.fields and self.instance and self.instance.pk and self.instance.fecha_hora:
            local_dt = localtime(self.instance.fecha_hora)
            self.initial['fecha_hora'] = local_dt.strftime('%Y-%m-%dT%H:%M')

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