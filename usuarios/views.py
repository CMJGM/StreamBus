from django.shortcuts import render
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm

def index(request):
    params = {}    
    return render(request,"base.html", params)

class RegisterView(FormView):
    template_name = "usuarios/registration_form.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)