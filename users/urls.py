from django.urls import path
from django.contrib.auth import views as auth_views
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
]
