from django.apps import AppConfig


class MainConfig(AppConfig):
    """
    Конфигурация приложения main.

    Основное приложение сайта, отвечающее за отображение
    статических страниц (главная, о проекте, правила, контакты).
    """
    name = 'main'
