from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

# Импортируем модели из game_quiz, так как главная страница взаимодействует с ними
from game_quiz.models import QuizGame, QuizQuestionSet


class MainViewsTest(TestCase):
    """Тестирование контроллеров (Views) главного приложения сайта"""

    @classmethod
    def setUpTestData(cls):
        # Создаем пользователя и набор вопросов для тестов активной игры
        cls.user = User.objects.create_user(username='main_tester', password='123')
        cls.q_set = QuizQuestionSet.objects.create(name='Пак для главной', owner=cls.user)

    def setUp(self):
        self.client = Client()

    def test_index_page_unauthenticated(self):
        """Главная страница для неавторизованного гостя"""
        response = self.client.get(reverse('main:index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/index.html')
        # У гостя точно не может быть активной игры
        self.assertIsNone(response.context.get('active_game'))

    def test_index_page_authenticated_no_active_game(self):
        """Главная страница для авторизованного юзера БЕЗ запущенных игр"""
        self.client.login(username='main_tester', password='123')
        response = self.client.get(reverse('main:index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/index.html')
        # Контекст 'active_game' должен быть пустым
        self.assertIsNone(response.context.get('active_game'))

    def test_index_page_authenticated_with_active_game(self):
        """
        Проверка важнейшей фичи: передача активной игры в контекст главной страницы,
        чтобы отобразилась плавающая панель возврата.
        """
        # Искусственно создаем активную игру (статус 'waiting' или 'playing')
        game = QuizGame.objects.create(
            owner=self.user,
            question_set=self.q_set,
            status='waiting',
            game_code=QuizGame.generate_unique_code()
        )

        self.client.login(username='main_tester', password='123')
        response = self.client.get(reverse('main:index'))

        self.assertEqual(response.status_code, 200)
        # Убеждаемся, что игра успешно передалась в HTML-шаблон
        self.assertIsNotNone(response.context.get('active_game'))
        self.assertEqual(response.context['active_game'].game_code, game.game_code)

    def test_about_page_renders_correctly(self):
        """Проверка доступности страницы 'О проекте'"""
        response = self.client.get(reverse('main:about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/about.html')

    def test_rules_page_renders_correctly(self):
        """Проверка доступности страницы 'Правила'"""
        response = self.client.get(reverse('main:rules'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/rules.html')

    def test_contacts_page_renders_correctly(self):
        """Проверка доступности страницы 'Контакты'"""
        response = self.client.get(reverse('main:contacts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/contacts.html')
