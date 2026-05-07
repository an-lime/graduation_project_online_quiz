from django.contrib.auth import views as auth_views
from django.urls import path

from users import views as user_views

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

    path('profile/', user_views.profile, name='profile'),
    path('profile/edit/', user_views.profile_edit, name='profile_edit'),
    path('profile/password-change/', user_views.password_change, name='password_change'),

    # AJAX пути
    path('ajax/send-code', user_views.send_verify_code, name='send_verify_code'),
    path('ajax/verify-code', user_views.verify_email_code, name='verify_email_code'),

    path('bot_api/user/<int:vk_id>/', user_views.api_get_user_by_vk, name='api_get_user_by_vk'),
]
