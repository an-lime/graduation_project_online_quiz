from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import TestCase

from users.utils import terminate_all_user_sessions


class UserProfileTests(TestCase):
    def test_create_user_profile_signal(self):
        """Тест создания профиля пользователя при создании пользователя"""
        user = User.objects.create_user(username='testuser', password='testpass')

        # Проверяем, что профиль был создан автоматически
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.user, user)

        # Проверяем, что роль по умолчанию - 'Участник'
        self.assertEqual(user.profile.role.name, 'Участник')

    def test_create_superuser_profile_signal(self):
        """Тест создания профиля суперпользователя с ролью Администратор"""
        admin = User.objects.create_superuser(username='admin', password='adminpass', email='admin@test.com')

        # Проверяем, что профиль был создан
        self.assertTrue(hasattr(admin, 'profile'))

        # Проверяем, что роль суперпользователя - 'Администратор'
        self.assertEqual(admin.profile.role.name, 'Администратор')


class TerminateSessionsTests(TestCase):
    def test_terminate_all_user_sessions(self):
        """Тест завершения всех сессий пользователя"""
        # Создаем пользователя
        user = User.objects.create_user(username='testuser', password='testpass')

        # Создаем несколько сессий для этого пользователя
        from django.contrib.sessions.backends.db import SessionStore

        session1 = SessionStore()
        session1['_auth_user_id'] = str(user.id)
        session1.save()

        session2 = SessionStore()
        session2['_auth_user_id'] = str(user.id)
        session2.save()

        # Создаем сессию для другого пользователя
        other_user = User.objects.create_user(username='otheruser', password='testpass')
        session3 = SessionStore()
        session3['_auth_user_id'] = str(other_user.id)
        session3.save()

        # Проверяем, что сессии существуют
        initial_sessions_count = Session.objects.count()
        self.assertEqual(initial_sessions_count, 3)

        # Вызываем функцию завершения сессий
        terminate_all_user_sessions(user)

        # Проверяем, что сессии пользователя удалены, но сессия другого пользователя осталась
        remaining_sessions = Session.objects.count()
        self.assertEqual(remaining_sessions, 1)

        # Проверяем, что оставшаяся сессия принадлежит другому пользователю
        remaining_session = Session.objects.first()
        session_data = remaining_session.get_decoded()
        self.assertEqual(str(session_data['_auth_user_id']), str(other_user.id))
