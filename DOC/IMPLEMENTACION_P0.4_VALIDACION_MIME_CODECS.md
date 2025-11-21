# P0.4 - Validación MIME Types y Codecs de Video

## Fecha: 2025-11-20

## Estado: ✅ IMPLEMENTADO

---

## Resumen Ejecutivo

Se implementó validación robusta de archivos multimedia:
- **Validación MIME type** del contenido real del archivo (no solo extensión)
- **Validación de codecs de video** (H.264, H.265, VP9, AV1)
- **Límites de tamaño** configurables por tipo de archivo

### Problema Resuelto

**Antes:** Solo se validaba la extensión del archivo
```python
# VULNERABLE - Un malware.exe renombrado a malware.jpg sería aceptado
if not imagen.name.lower().endswith(('.jpg', '.jpeg', '.png')):
    raise ValidationError("Solo se permiten .jpg, .jpeg o .png")
```

**Después:** Validación completa del contenido
```python
# SEGURO - Verifica MIME type real del archivo
validate_image_file(imagen)  # Usa python-magic + Pillow

# Para videos, además valida el codec
video_info = validate_video_file(video, validate_codec=True)
# Verifica: H.264, H.265, VP9, AV1, MPEG-4
```

---

## Componentes Implementados

### 1. `informes/validators.py` (NUEVO)

Módulo completo de validación con:

#### Funciones de Detección
- `get_mime_type_magic()` - MIME type usando python-magic
- `get_mime_type_pillow()` - MIME type usando Pillow (fallback)
- `get_video_info_ffprobe()` - Análisis de video con ffprobe
- `is_ffprobe_available()` - Verifica disponibilidad de ffprobe

#### Validadores Principales
- `validate_image_file()` - Valida imágenes (MIME + tamaño)
- `validate_video_file()` - Valida videos (MIME + codec + tamaño)
- `validate_video_codec()` - Valida codec específico

#### Clases para Django Forms
- `ImageValidator` - Validador de imágenes
- `VideoValidator` - Validador de videos

#### Utilidades
- `get_video_codec_info()` - Info sobre un codec
- `get_supported_codecs()` - Lista de codecs soportados
- `check_dependencies()` - Estado de dependencias

---

### 2. Codecs de Video Soportados

| Codec | Nombre | Calidad | Compatibilidad |
|-------|--------|---------|----------------|
| `h264` / `avc1` | H.264 / AVC | Buena | Excelente |
| `hevc` / `hev1` | H.265 / HEVC | Excelente | Buena |
| `vp9` | VP9 | Excelente | Buena |
| `av1` | AV1 | Excelente | Limitada |
| `mpeg4` | MPEG-4 Part 2 | Regular | Buena |
| `mjpeg` | Motion JPEG | Regular | Buena |

---

### 3. MIME Types Permitidos

#### Imágenes
```python
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
}
```

#### Videos
```python
ALLOWED_VIDEO_MIME_TYPES = {
    'video/mp4': ['.mp4', '.m4v'],
    'video/x-msvideo': ['.avi'],
    'video/quicktime': ['.mov'],
    'video/x-matroska': ['.mkv'],
    'video/webm': ['.webm'],
}
```

---

### 4. Límites de Tamaño

| Tipo | Límite Default | Configurable |
|------|---------------|--------------|
| Imagen | 10 MB | `MAX_IMAGE_UPLOAD_SIZE_MB` |
| Video | 60 MB | `MAX_VIDEO_UPLOAD_SIZE_MB` |

---

## Archivos Modificados

### 1. `informes/validators.py` (NUEVO)
- ~500 líneas de código
- Validadores completos para imágenes y videos
- Soporte para python-magic y ffprobe

### 2. `informes/forms.py`
**FotoInformeForm:**
```python
def clean_imagen(self):
    imagen = self.cleaned_data.get('imagen')
    if imagen:
        validate_image_file(imagen)  # NUEVO: Validación MIME
    return imagen
```

**VideoForm:**
```python
def clean_video(self):
    video = self.cleaned_data.get('video')
    if video:
        video_info = validate_video_file(video, validate_codec=True)
        if video_info:
            self._video_info = video_info  # Guarda info del codec
    return video
```

### 3. `StreamBus/settings.py`
```python
MAX_VIDEO_UPLOAD_SIZE_MB = config('MAX_VIDEO_UPLOAD_SIZE_MB', default=60, cast=int)
MAX_IMAGE_UPLOAD_SIZE_MB = config('MAX_IMAGE_UPLOAD_SIZE_MB', default=10, cast=int)
```

### 4. `requirements.txt`
```
python-magic==0.4.27
python-magic-bin==0.4.14
```

### 5. `.env.example`
```env
MAX_VIDEO_UPLOAD_SIZE_MB=60
MAX_IMAGE_UPLOAD_SIZE_MB=10
# Validación de videos (requiere ffprobe/ffmpeg instalado)
```

---

## Instalación

### 1. Instalar Dependencias Python

```bash
pip install -r requirements.txt
```

Esto instalará:
- `python-magic==0.4.27` - Detección MIME type
- `python-magic-bin==0.4.14` - Binarios de libmagic (Windows)

### 2. Instalar FFmpeg (Opcional, para validación de codecs)

#### Windows
1. Descargar de: https://ffmpeg.org/download.html
2. Extraer a `C:\ffmpeg`
3. Agregar `C:\ffmpeg\bin` al PATH
4. Verificar: `ffprobe -version`

#### Linux
```bash
sudo apt install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

### 3. Verificar Dependencias

```python
from informes.validators import check_dependencies
print(check_dependencies())
# {'python_magic': True, 'pillow': True, 'ffprobe': True}
```

---

## Uso

### Validación Automática en Forms

Los forms `FotoInformeForm` y `VideoForm` ya usan los validadores automáticamente.

```python
# En una vista
form = VideoForm(request.POST, request.FILES)
if form.is_valid():
    video = form.save()

    # Obtener info del codec (si ffprobe está disponible)
    video_info = form.get_video_info()
    if video_info:
        print(f"Codec: {video_info['video_codec']}")
        print(f"Resolución: {video_info['width']}x{video_info['height']}")
```

### Validación Manual

```python
from informes.validators import (
    validate_image_file,
    validate_video_file,
    get_video_codec_info,
)

# Validar imagen
try:
    validate_image_file(uploaded_file)
except ValidationError as e:
    print(f"Error: {e}")

# Validar video con info de codec
try:
    video_info = validate_video_file(uploaded_file, validate_codec=True)
    if video_info:
        codec_info = get_video_codec_info(video_info['video_codec'])
        print(f"Codec: {codec_info['name']}")
        print(f"Calidad: {codec_info['quality']}")
except ValidationError as e:
    print(f"Error: {e}")
```

---

## Comportamiento de Fallback

El sistema tiene múltiples niveles de fallback:

### Nivel 1: python-magic disponible
- ✅ Detección MIME type precisa
- ✅ Valida contenido real del archivo
- ✅ Previene archivos renombrados

### Nivel 2: Solo Pillow (imágenes)
- ✅ Verifica que sea imagen válida
- ⚠️ Menos preciso que python-magic

### Nivel 3: Solo extensión (fallback final)
- ⚠️ Valida solo extensión del archivo
- ⚠️ Log de advertencia generado
- ❌ No previene archivos renombrados

### Para videos + ffprobe
- ✅ Análisis completo de codec
- ✅ Info de resolución, duración, bitrate
- ✅ Validación de codec permitido

### Para videos sin ffprobe
- ✅ Validación MIME type
- ⚠️ Sin validación de codec específico

---

## Logging

El sistema genera logs informativos:

```python
# En settings.py, agregar logger
LOGGING = {
    'loggers': {
        'informes.validators': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}
```

**Ejemplos de logs:**

```
INFO Imagen validada: foto.jpg, tamaño: 2456789 bytes, tipo: image/jpeg
INFO Video validado: video.mp4, codec: H.264 / AVC, resolución: 1920x1080, duración: 45.2s
WARNING ffprobe no disponible. Saltando validación de codec.
WARNING Usando validación por extensión (librerías no disponibles)
```

---

## Seguridad

### Vulnerabilidades Prevenidas

1. **Bypass por extensión**
   - ❌ Antes: `malware.exe` → `malware.jpg` aceptado
   - ✅ Ahora: Rechazado por MIME type incorrecto

2. **Archivos corruptos**
   - ❌ Antes: Archivo dañado aceptado si extensión OK
   - ✅ Ahora: Pillow/ffprobe detectan archivo inválido

3. **Codecs no soportados**
   - ❌ Antes: Cualquier video .mp4 aceptado
   - ✅ Ahora: Solo codecs permitidos (H.264, etc.)

4. **Archivos muy grandes**
   - ❌ Antes: Límite solo en algunos lugares
   - ✅ Ahora: Límite configurable por tipo

### Recomendaciones Adicionales

1. **Antivirus en uploads:**
   ```python
   # Opcional: Integrar con ClamAV
   import clamd
   cd = clamd.ClamdUnixSocket()
   cd.scan(file_path)
   ```

2. **Cuarentena de archivos:**
   ```python
   # Mover a carpeta temporal antes de validar
   UPLOAD_QUARANTINE_PATH = '/tmp/quarantine/'
   ```

---

## Testing

### Test Manual

```bash
# 1. Archivo válido - debe aceptarse
# Subir un JPG/PNG real

# 2. Archivo inválido - debe rechazarse
# Renombrar un .exe a .jpg e intentar subir
# Esperado: "Tipo de archivo no permitido: application/x-dosexec"

# 3. Video con codec no soportado
# Subir video con codec antiguo (ej: DivX)
# Esperado: "Codec de video no soportado: divx"

# 4. Archivo muy grande
# Subir imagen > 10MB
# Esperado: "El archivo excede el tamaño máximo permitido de 10 MB"
```

### Test Automático

```python
# TEST/informes/test_validators.py
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from informes.validators import validate_image_file, validate_video_file

class ValidatorTestCase(TestCase):
    def test_invalid_image_extension(self):
        """Rechazar archivo con extensión incorrecta"""
        fake_image = SimpleUploadedFile(
            "malware.exe",
            b"MZ\x90\x00",  # Header de EXE
            content_type="application/x-msdownload"
        )
        with self.assertRaises(ValidationError):
            validate_image_file(fake_image)
```

---

## Configuración Avanzada

### Personalizar Codecs Permitidos

```python
# En una vista específica
from informes.validators import VideoValidator

class MyVideoForm(forms.Form):
    video = forms.FileField(
        validators=[VideoValidator(
            max_size_mb=100,
            validate_codec=True,
            allowed_codecs=['h264', 'hevc']  # Solo H.264 y H.265
        )]
    )
```

### Deshabilitar Validación de Codec

```python
video_info = validate_video_file(file, validate_codec=False)
# Solo valida MIME type y tamaño
```

---

## Métricas

| Métrica | Valor |
|---------|-------|
| Líneas de código | ~500 |
| Archivos modificados | 5 |
| Dependencias agregadas | 2 |
| Codecs soportados | 6 |
| MIME types imagen | 3 |
| MIME types video | 5 |

---

## Referencias

- [python-magic](https://github.com/ahupp/python-magic)
- [ffprobe documentation](https://ffmpeg.org/ffprobe.html)
- [Pillow Image verification](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify)
- [OWASP File Upload](https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload)

---

**Estado:** ✅ IMPLEMENTADO

**Próximo:** P0.5 - Path Traversal Prevention
