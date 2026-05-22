"""
Модуль конфигурации приложения пользователей.

Содержит класс конфигурации Django application для приложения users.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Класс конфигурации приложения users.

    Определяет метаданные приложения для системы Django.
    """
    name = 'users'
