from django.urls import path
from django.contrib.auth import views as auth_views
from .views import RegisterView, CustomLoginView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='usuarios/logout.html'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='usuarios/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='usuarios/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='usuarios/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='usuarios/password_reset_complete.html'), name='password_reset_complete'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
