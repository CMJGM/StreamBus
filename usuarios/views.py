from django.shortcuts import render, redirect
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
import logging

logger = logging.getLogger('usuarios.views')


def index(request):
    params = {}
    return render(request,"base.html", params)


class CustomLoginView(LoginView):
    """Vista de login personalizada con logging mejorado"""
    template_name = "usuarios/login.html"

    def form_invalid(self, form):
        """Llamado cuando el formulario tiene errores"""
        username = form.cleaned_data.get('username', 'unknown')
        logger.warning(f"Login fallido para usuario: {username}")
        logger.debug(f"Errores del formulario: {form.errors}")
        return super().form_invalid(form)

    def form_valid(self, form):
        """Llamado cuando el login es exitoso"""
        username = form.cleaned_data.get('username')
        # Primero completar el login (esto autentica al usuario)
        response = super().form_valid(form)
        # DESPUÉS loguear (ahora request.user ya es el usuario autenticado)
        logger.info(f"Login exitoso para usuario: {username}")
        return response


class RegisterView(FormView):
    template_name = "usuarios/registration_form.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)