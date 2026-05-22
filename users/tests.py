from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from users.models import UserRole, UserProfile


class UsersModelsAndSignalsTest(TestCase):
    """1. Тестирование моделей и автоматических сигналов (Signals)"""

    def test_standard_user_profile_creation(self):
        """
        Проверка сигнала: при создании обычного пользователя
        должен автоматически создаться профиль с ролью 'Участник'.
        """
        user = User.objects.create_user(username='ordinary_player', password='123')

        # Проверяем, что профиль физически существует в БД
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

        # Проверяем, что сигнал корректно назначил базовую роль
        self.assertIsNotNone(user.profile.role)
        self.assertEqual(user.profile.role.name, 'Участник')

    def test_superuser_profile_creation(self):
        """
        Проверка сигнала: при создании суперпользователя
        должна автоматически назначаться роль 'Администратор'.
        """
        admin = User.objects.create_superuser(username='super_admin', email='admin@test.com', password='123')

        # Проверяем, что профиль создан
        self.assertTrue(hasattr(admin, 'profile'))

        # Проверяем, что сигнал распознал is_superuser и выдал нужную роль
        self.assertEqual(admin.profile.role.name, 'Администратор')

    def test_models_string_representation(self):
        """Проверка строкового отображения (__str__) моделей для админки"""
        role = UserRole.objects.create(name='Тестовая роль')
        self.assertEqual(str(role), 'Тестовая роль')

        user = User.objects.create_user(username='test_str_user', password='123')
        self.assertEqual(str(user.profile), 'test_str_user')

    def test_vk_id_uniqueness_and_saving(self):
        """Проверка сохранения VK ID в профиль"""
        user = User.objects.create_user(username='vk_user', password='123')

        # Имитируем привязку ВК к созданному профилю
        user.profile.vk_id = 123456789
        user.profile.save()

        # Достаем из базы и проверяем
        updated_profile = UserProfile.objects.get(user=user)
        self.assertEqual(updated_profile.vk_id, 123456789)


class UsersViewsTest(TestCase):
    """2. Тестирование контроллеров (Views) и прав доступа"""

    def setUp(self):
        self.client = Client()
        # При создании юзера сигнал сам создаст UserProfile
        self.user = User.objects.create_user(username='test_user', password='password123')

        # Задаем namespace url'ов
        self.profile_url = reverse('users:profile') if 'users' else '/users/profile/'
        self.login_url = reverse('users:login') if 'users' else '/users/login/'

    def test_profile_access_authenticated(self):
        """Авторизованный пользователь должен успешно попадать в профиль"""
        self.client.login(username='test_user', password='password123')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')

    def test_profile_access_unauthenticated(self):
        """Неавторизованного пользователя должно перекидывать на страницу логина"""
        response = self.client.get(self.profile_url)

        # Ожидаем редирект (302) на страницу входа
        self.assertEqual(response.status_code, 302)
        # Проверяем, что в адресе редиректа есть URL логина
        self.assertTrue(response.url.startswith(self.login_url))

    def test_login_page_renders(self):
        """Страница логина должна корректно открываться (GET-запрос)"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_user_logout(self):
        """Тест выхода пользователя из системы"""
        # Сначала логинимся
        self.client.login(username='test_user', password='password123')

        # Вызываем встроенный logout Django строго через POST-запрос
        logout_url = reverse('users:logout')
        response = self.client.post(logout_url)

        # Должен произойти редирект после выхода
        self.assertEqual(response.status_code, 302)

        # Пытаемся зайти в профиль после логаута — должно отказать
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, 302)
