"""
Validadores de archivos multimedia para informes.

Este módulo proporciona validación robusta de archivos multimedia:
- Validación MIME type (contenido real del archivo)
- Validación de codecs de video (H.264, H.265, VP9, AV1)
- Límites de tamaño por tipo de archivo

Dependencias opcionales:
- python-magic: Para validación MIME type avanzada
- ffprobe (ffmpeg): Para análisis de codecs de video
- Pillow: Para validación de imágenes (ya instalado)

Si las dependencias no están disponibles, se usa validación por extensión como fallback.
"""

import os
import subprocess
import json
import logging
from django.core.exceptions import ValidationError
from django.conf import settings

logger = logging.getLogger('informes.validators')

# ============================================================================
# CONFIGURACIÓN DE CODECS Y MIME TYPES PERMITIDOS
# ============================================================================

# MIME types permitidos para imágenes
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],  # Opcional
}

# MIME types permitidos para videos
ALLOWED_VIDEO_MIME_TYPES = {
    'video/mp4': ['.mp4', '.m4v'],
    'video/x-msvideo': ['.avi'],
    'video/quicktime': ['.mov'],
    'video/x-matroska': ['.mkv'],
    'video/webm': ['.webm'],
}

# Codecs de video permitidos (nombre ffprobe -> descripción)
ALLOWED_VIDEO_CODECS = {
    # H.264 / AVC - El más común y compatible
    'h264': {
        'name': 'H.264 / AVC',
        'description': 'Codec más compatible, recomendado para web',
        'quality': 'good',
        'compatibility': 'excellent',
    },
    'avc1': {
        'name': 'H.264 / AVC',
        'description': 'Variante de H.264',
        'quality': 'good',
        'compatibility': 'excellent',
    },
    # H.265 / HEVC - Mejor compresión, menos compatible
    'hevc': {
        'name': 'H.265 / HEVC',
        'description': 'Mejor compresión que H.264, menos compatible',
        'quality': 'excellent',
        'compatibility': 'good',
    },
    'hev1': {
        'name': 'H.265 / HEVC',
        'description': 'Variante de H.265',
        'quality': 'excellent',
        'compatibility': 'good',
    },
    # VP9 - Codec de Google, buena compresión
    'vp9': {
        'name': 'VP9',
        'description': 'Codec de Google, buena compresión, compatible con Chrome',
        'quality': 'excellent',
        'compatibility': 'good',
    },
    # AV1 - Codec más moderno, mejor compresión
    'av1': {
        'name': 'AV1',
        'description': 'Codec más moderno, excelente compresión',
        'quality': 'excellent',
        'compatibility': 'limited',
    },
    # MPEG-4 Part 2 - Antiguo pero común
    'mpeg4': {
        'name': 'MPEG-4 Part 2',
        'description': 'Codec antiguo, compatible',
        'quality': 'fair',
        'compatibility': 'good',
    },
    # MJPEG - Para cámaras
    'mjpeg': {
        'name': 'Motion JPEG',
        'description': 'Común en cámaras de seguridad',
        'quality': 'fair',
        'compatibility': 'good',
    },
}

# Codecs de audio permitidos
ALLOWED_AUDIO_CODECS = {
    'aac': 'AAC - Recomendado',
    'mp3': 'MP3 - Compatible',
    'ac3': 'AC3 / Dolby Digital',
    'opus': 'Opus - Moderno',
    'vorbis': 'Vorbis - Open source',
    'pcm_s16le': 'PCM sin comprimir',
    'pcm_s24le': 'PCM sin comprimir (24 bit)',
}

# Límites de tamaño (en MB)
FILE_SIZE_LIMITS = {
    'image': getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE_MB', 10),  # 10 MB por defecto
    'video': getattr(settings, 'MAX_VIDEO_UPLOAD_SIZE_MB', 60),  # 60 MB por defecto
}

# ============================================================================
# FUNCIONES DE DETECCIÓN
# ============================================================================

def get_mime_type_magic(file_obj):
    """
    Obtiene el MIME type real del archivo usando python-magic.

    Args:
        file_obj: Archivo de Django (InMemoryUploadedFile o TemporaryUploadedFile)

    Returns:
        str: MIME type del archivo o None si no se puede determinar
    """
    try:
        import magic

        # Leer los primeros bytes del archivo
        file_obj.seek(0)
        header = file_obj.read(2048)  # Leer primeros 2KB
        file_obj.seek(0)  # Volver al inicio

        # Detectar MIME type
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(header)

        logger.debug(f"MIME type detectado (magic): {mime_type}")
        return mime_type

    except ImportError:
        logger.warning("python-magic no está instalado. Usando validación alternativa.")
        return None
    except Exception as e:
        logger.error(f"Error detectando MIME type: {e}")
        return None


def get_mime_type_pillow(file_obj):
    """
    Obtiene el MIME type de una imagen usando Pillow.

    Args:
        file_obj: Archivo de imagen

    Returns:
        str: MIME type de la imagen o None
    """
    try:
        from PIL import Image

        file_obj.seek(0)
        img = Image.open(file_obj)
        img.verify()  # Verifica que sea una imagen válida
        file_obj.seek(0)

        # Mapear formato PIL a MIME type
        format_to_mime = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'GIF': 'image/gif',
            'BMP': 'image/bmp',
            'WEBP': 'image/webp',
        }

        mime_type = format_to_mime.get(img.format)
        logger.debug(f"MIME type detectado (Pillow): {mime_type}")
        return mime_type

    except Exception as e:
        logger.debug(f"No es una imagen válida: {e}")
        return None


def get_video_info_ffprobe(file_path):
    """
    Obtiene información detallada del video usando ffprobe.

    Args:
        file_path: Ruta al archivo de video

    Returns:
        dict: Información del video o None si hay error
        {
            'duration': float,  # Duración en segundos
            'video_codec': str,  # Codec de video
            'video_codec_long': str,  # Nombre completo del codec
            'audio_codec': str,  # Codec de audio
            'width': int,  # Ancho en pixels
            'height': int,  # Alto en pixels
            'fps': float,  # Frames por segundo
            'bitrate': int,  # Bitrate en bits/s
        }
    """
    try:
        # Comando ffprobe
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # Timeout de 30 segundos
        )

        if result.returncode != 0:
            logger.warning(f"ffprobe falló: {result.stderr}")
            return None

        data = json.loads(result.stdout)

        # Extraer información de video
        video_info = {}

        # Buscar stream de video
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_info['video_codec'] = stream.get('codec_name', 'unknown')
                video_info['video_codec_long'] = stream.get('codec_long_name', 'Unknown')
                video_info['width'] = stream.get('width', 0)
                video_info['height'] = stream.get('height', 0)

                # Calcular FPS
                fps_str = stream.get('r_frame_rate', '0/1')
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    video_info['fps'] = float(num) / float(den) if float(den) > 0 else 0
                else:
                    video_info['fps'] = float(fps_str)

            elif stream.get('codec_type') == 'audio':
                video_info['audio_codec'] = stream.get('codec_name', 'unknown')

        # Información del formato
        format_info = data.get('format', {})
        video_info['duration'] = float(format_info.get('duration', 0))
        video_info['bitrate'] = int(format_info.get('bit_rate', 0))
        video_info['format'] = format_info.get('format_name', 'unknown')

        logger.debug(f"Información de video (ffprobe): {video_info}")
        return video_info

    except FileNotFoundError:
        logger.warning("ffprobe no está instalado. Instalar ffmpeg para validación de codecs.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("ffprobe timeout - archivo muy grande o corrupto")
        return None
    except Exception as e:
        logger.error(f"Error ejecutando ffprobe: {e}")
        return None


def is_ffprobe_available():
    """Verifica si ffprobe está disponible en el sistema."""
    try:
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


# ============================================================================
# VALIDADORES
# ============================================================================

def validate_image_file(file_obj):
    """
    Valida que un archivo sea una imagen válida.

    Validaciones:
    1. Tamaño máximo del archivo
    2. MIME type real (contenido del archivo)
    3. Extensión coincide con MIME type

    Args:
        file_obj: Archivo de imagen de Django

    Raises:
        ValidationError: Si el archivo no es válido
    """
    if not file_obj:
        return

    # 1. Validar tamaño
    max_size_mb = FILE_SIZE_LIMITS['image']
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_obj.size > max_size_bytes:
        raise ValidationError(
            f"El archivo excede el tamaño máximo permitido de {max_size_mb} MB. "
            f"Tamaño actual: {file_obj.size / (1024*1024):.1f} MB"
        )

    # 2. Validar MIME type
    mime_type = get_mime_type_magic(file_obj) or get_mime_type_pillow(file_obj)

    if mime_type:
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValidationError(
                f"Tipo de archivo no permitido: {mime_type}. "
                f"Solo se permiten imágenes: JPEG, PNG"
            )

        # 3. Validar que la extensión coincida con el MIME type
        ext = os.path.splitext(file_obj.name)[1].lower()
        allowed_extensions = ALLOWED_IMAGE_MIME_TYPES.get(mime_type, [])

        if ext not in allowed_extensions:
            raise ValidationError(
                f"La extensión del archivo ({ext}) no coincide con su contenido ({mime_type}). "
                f"Posible archivo manipulado."
            )
    else:
        # Fallback: validar solo por extensión
        logger.warning("Usando validación por extensión (librerías no disponibles)")
        ext = os.path.splitext(file_obj.name)[1].lower()
        all_extensions = [e for exts in ALLOWED_IMAGE_MIME_TYPES.values() for e in exts]

        if ext not in all_extensions:
            raise ValidationError(
                f"Extensión no permitida: {ext}. "
                f"Solo se permiten: {', '.join(all_extensions)}"
            )

    logger.info(f"Imagen validada: {file_obj.name}, tamaño: {file_obj.size} bytes, tipo: {mime_type}")


def validate_video_file(file_obj, validate_codec=True):
    """
    Valida que un archivo sea un video válido.

    Validaciones:
    1. Tamaño máximo del archivo
    2. MIME type real (contenido del archivo)
    3. Codec de video permitido (si ffprobe está disponible)
    4. Extensión coincide con MIME type

    Args:
        file_obj: Archivo de video de Django
        validate_codec: Si True, valida el codec de video

    Raises:
        ValidationError: Si el archivo no es válido

    Returns:
        dict: Información del video si se validó con ffprobe, None si no
    """
    if not file_obj:
        return None

    # 1. Validar tamaño
    max_size_mb = FILE_SIZE_LIMITS['video']
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_obj.size > max_size_bytes:
        raise ValidationError(
            f"El video excede el tamaño máximo permitido de {max_size_mb} MB. "
            f"Tamaño actual: {file_obj.size / (1024*1024):.1f} MB"
        )

    # 2. Validar MIME type
    mime_type = get_mime_type_magic(file_obj)

    if mime_type:
        if mime_type not in ALLOWED_VIDEO_MIME_TYPES:
            raise ValidationError(
                f"Tipo de archivo no permitido: {mime_type}. "
                f"Solo se permiten videos: MP4, AVI, MOV, MKV, WEBM"
            )

        # 3. Validar que la extensión coincida con el MIME type
        ext = os.path.splitext(file_obj.name)[1].lower()
        allowed_extensions = ALLOWED_VIDEO_MIME_TYPES.get(mime_type, [])

        if ext not in allowed_extensions:
            logger.warning(
                f"Extensión ({ext}) no coincide con MIME type ({mime_type}). "
                f"Permitiendo por compatibilidad."
            )
    else:
        # Fallback: validar solo por extensión
        logger.warning("Usando validación por extensión para video")
        ext = os.path.splitext(file_obj.name)[1].lower()
        all_extensions = [e for exts in ALLOWED_VIDEO_MIME_TYPES.values() for e in exts]

        if ext not in all_extensions:
            raise ValidationError(
                f"Extensión no permitida: {ext}. "
                f"Solo se permiten: {', '.join(all_extensions)}"
            )

    # 4. Validar codec de video (si está habilitado y ffprobe disponible)
    video_info = None
    if validate_codec and is_ffprobe_available():
        # Guardar temporalmente el archivo para analizarlo
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            file_obj.seek(0)
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            video_info = get_video_info_ffprobe(tmp_path)

            if video_info:
                codec = video_info.get('video_codec', '').lower()

                if codec not in ALLOWED_VIDEO_CODECS:
                    codec_names = [info['name'] for info in ALLOWED_VIDEO_CODECS.values()]
                    raise ValidationError(
                        f"Codec de video no soportado: {codec}. "
                        f"Codecs permitidos: {', '.join(set(codec_names))}"
                    )

                codec_info = ALLOWED_VIDEO_CODECS[codec]
                logger.info(
                    f"Video validado: {file_obj.name}, "
                    f"codec: {codec_info['name']}, "
                    f"resolución: {video_info.get('width')}x{video_info.get('height')}, "
                    f"duración: {video_info.get('duration', 0):.1f}s"
                )
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(tmp_path)
            except:
                pass
            file_obj.seek(0)
    else:
        logger.info(f"Video validado (sin análisis de codec): {file_obj.name}")

    return video_info


def validate_video_codec(file_path):
    """
    Valida el codec de un archivo de video.

    Args:
        file_path: Ruta al archivo de video

    Returns:
        dict: Información del video incluyendo codec

    Raises:
        ValidationError: Si el codec no está permitido
    """
    if not is_ffprobe_available():
        logger.warning("ffprobe no disponible. Saltando validación de codec.")
        return None

    video_info = get_video_info_ffprobe(file_path)

    if not video_info:
        raise ValidationError("No se pudo analizar el archivo de video")

    codec = video_info.get('video_codec', '').lower()

    if codec not in ALLOWED_VIDEO_CODECS:
        codec_names = list(set([info['name'] for info in ALLOWED_VIDEO_CODECS.values()]))
        raise ValidationError(
            f"Codec de video no soportado: {codec}. "
            f"Codecs permitidos: {', '.join(codec_names)}"
        )

    return video_info


# ============================================================================
# VALIDADORES PARA DJANGO FORMS
# ============================================================================

class ImageValidator:
    """
    Validador de imágenes para usar en forms de Django.

    Uso:
        class MiForm(forms.ModelForm):
            imagen = forms.ImageField(validators=[ImageValidator()])
    """

    def __init__(self, max_size_mb=None, allowed_types=None):
        self.max_size_mb = max_size_mb or FILE_SIZE_LIMITS['image']
        self.allowed_types = allowed_types or list(ALLOWED_IMAGE_MIME_TYPES.keys())

    def __call__(self, file_obj):
        validate_image_file(file_obj)


class VideoValidator:
    """
    Validador de videos para usar en forms de Django.

    Uso:
        class MiForm(forms.ModelForm):
            video = forms.FileField(validators=[VideoValidator()])
    """

    def __init__(self, max_size_mb=None, validate_codec=True, allowed_codecs=None):
        self.max_size_mb = max_size_mb or FILE_SIZE_LIMITS['video']
        self.validate_codec = validate_codec
        self.allowed_codecs = allowed_codecs or list(ALLOWED_VIDEO_CODECS.keys())

    def __call__(self, file_obj):
        validate_video_file(file_obj, validate_codec=self.validate_codec)


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_video_codec_info(codec_name):
    """
    Obtiene información sobre un codec de video.

    Args:
        codec_name: Nombre del codec (ej: 'h264', 'hevc')

    Returns:
        dict: Información del codec o None si no está soportado
    """
    return ALLOWED_VIDEO_CODECS.get(codec_name.lower())


def get_supported_codecs():
    """
    Retorna lista de codecs soportados con su información.

    Returns:
        list: Lista de dicts con información de cada codec
    """
    seen = set()
    codecs = []

    for codec_id, info in ALLOWED_VIDEO_CODECS.items():
        if info['name'] not in seen:
            seen.add(info['name'])
            codecs.append({
                'id': codec_id,
                **info
            })

    return codecs


def check_dependencies():
    """
    Verifica qué dependencias están disponibles para validación.

    Returns:
        dict: Estado de cada dependencia
    """
    status = {
        'python_magic': False,
        'pillow': False,
        'ffprobe': False,
    }

    try:
        import magic
        status['python_magic'] = True
    except ImportError:
        pass

    try:
        from PIL import Image
        status['pillow'] = True
    except ImportError:
        pass

    status['ffprobe'] = is_ffprobe_available()

    return status
