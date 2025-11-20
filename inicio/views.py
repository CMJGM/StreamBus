from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def inicio(request):
    grupos_usuario = list(request.user.groups.values_list('name', flat=True))
    return render(request, 'inicio/inicio.html', {
        'user_groups': grupos_usuario
    })
