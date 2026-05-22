"""
Модуль утилит приложения пользователей.

Содержит вспомогательные функции для управления сессиями пользователей
и генерации кодов верификации.
"""

import random
import string

from django.contrib.sessions.models import Session
from django.utils import timezone


def terminate_all_user_sessions(user):
    """
    Завершение всех активных сессий пользователя.

    Удаляет все сессии указанного пользователя из базы данных,
    что приводит к его выходу из системы на всех устройствах.
    Используется после смены пароля в целях безопасности.

    Args:
        user: Экземпляр модели пользователя, чьи сессии нужно завершить.
    """
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get('_auth_user_id')) == str(user.id):
            session.delete()


def generate_verification_code(length=6):
    """
    Генерация случайного числового кода верификации.

    Создает код указанной длины, состоящий только из цифр.
    По умолчанию генерирует 6-значный код.

    Args:
        length: Длина кода (по умолчанию 6).

    Returns:
        Строка, содержащая случайный числовой код.
    """
    return ''.join(random.choices(string.digits, k=length))
