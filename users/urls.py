"""
Модуль маршрутизации URL приложения пользователей.

Определяет URL-паттерны для всех представлений, связанных с пользователями:
аутентификация, управление профилем, верификация email и API для бота.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from users import views as user_views

# Пространство имен для обратных ссылок на URL приложения users
app_name = 'users'

urlpatterns = [
    # Страница входа с использованием встроенного представления Django
    path('login/', user_views.login_view, name='login'),

    # Выход из системы с перенаправлением на главную страницу
    path('logout/', auth_views.LogoutView.as_view(
        next_page='main:index'
    ), name='logout'),

    # Управление профилем пользователя
    path('profile/', user_views.profile, name='profile'),
    path('profile/edit/', user_views.profile_edit, name='profile_edit'),
    path('profile/password-change/', user_views.password_change, name='password_change'),

    # AJAX endpoints для верификации email
    path('ajax/send-code', user_views.send_verify_code, name='send_verify_code'),
    path('ajax/verify-code', user_views.verify_email_code, name='verify_email_code'),

    # API endpoint для получения данных пользователя по VK ID (используется ботом)
    path('bot_api/user/<int:vk_id>/', user_views.api_get_user_by_vk, name='api_get_user_by_vk'),
]
