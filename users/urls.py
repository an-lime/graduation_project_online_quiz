from django.contrib.auth import views as auth_views
from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
        redirect_authenticated_user=True,
        extra_context={'next': ''}
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        next_page='main:index'
    ), name='logout'),

    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/password-change/', views.password_change, name='password_change'),

    #     AJAX пути
    path('ajax/send-code', views.send_verify_code, name='send_verify_code'),
    path('ajax/verify-code', views.verify_email_code, name='verify_email_code')
]
