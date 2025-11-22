"""
Vista de prueba para verificar logging con usuario
URL: /sit/test-logging/
"""

import logging
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

logger = logging.getLogger('sit.test_logging')


def test_logging_anonymous(request):
    """Vista de prueba - usuario anónimo"""
    logger.info("TEST: Vista accedida por usuario anónimo")
    logger.debug(f"TEST: Request user = {request.user}")
    logger.debug(f"TEST: Is authenticated = {request.user.is_authenticated}")

    html = """
    <html>
    <head><title>Test Logging</title></head>
    <body>
        <h1>Test de Logging - Usuario Anónimo</h1>
        <p>Usuario actual: {user}</p>
        <p>Autenticado: {auth}</p>
        <p>Verifica el archivo debug.log - deberías ver:</p>
        <pre>
YYYY-MM-DD HH:MM:SS | AnonymousUser | INFO | sit.test_logging | TEST: Vista accedida...
        </pre>
        <p><a href="/sit/test-logging-auth/">Ir a versión con login requerido</a></p>
        <p><a href="/admin/">Ir a login de admin</a></p>
    </body>
    </html>
    """

    return HttpResponse(html.format(
        user=request.user,
        auth=request.user.is_authenticated
    ))


@login_required
def test_logging_authenticated(request):
    """Vista de prueba - usuario autenticado"""
    logger.info(f"TEST: Vista accedida por usuario autenticado: {request.user.username}")
    logger.debug(f"TEST: Request user = {request.user}")
    logger.debug(f"TEST: User ID = {request.user.id}")
    logger.debug(f"TEST: Is staff = {request.user.is_staff}")

    html = """
    <html>
    <head><title>Test Logging - Autenticado</title></head>
    <body>
        <h1>Test de Logging - Usuario Autenticado</h1>
        <p>Usuario actual: <strong>{username}</strong></p>
        <p>ID: {user_id}</p>
        <p>Staff: {is_staff}</p>
        <p>Verifica el archivo debug.log - deberías ver:</p>
        <pre>
YYYY-MM-DD HH:MM:SS | {username} | INFO | sit.test_logging | TEST: Vista accedida...
        </pre>
        <p><strong>Si ves "system" en lugar de "{username}", el middleware NO está funcionando.</strong></p>
        <p><a href="/sit/test-logging/">Ir a versión sin login</a></p>
        <p><a href="/admin/logout/">Logout</a></p>
    </body>
    </html>
    """

    return HttpResponse(html.format(
        username=request.user.username,
        user_id=request.user.id,
        is_staff=request.user.is_staff
    ))
