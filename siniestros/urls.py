from django.urls import path
from siniestros import views

urlpatterns = [
    path("", views.index, name="index"),
]
