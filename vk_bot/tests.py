from unittest.mock import patch, AsyncMock, MagicMock

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TestCase

from game_quiz.models import QuizGame, GameResult, QuizQuestionSet
# Импорты моделей
from users.models import UserRole
from vk_bot.handlers.callback_handlers.game_callback_handler import join_game
from vk_bot.handlers.callback_handlers.main_callback_handler import create_profile
# Импорты хэндлеров
from vk_bot.handlers.main_handler import start_command
# Импорты утилит бота
from vk_bot.utils.db import get_current_user, create_user_and_profile, get_user_stats
from vk_bot.utils.states import set_state, get_state, clear_state, UserState


# === ИМИТАЦИЯ ОБЪЕКТОВ VKBOTTLE ===
class MockMessage:
    """Мок для обычного текстового сообщения (Message)"""

    def __init__(self, from_id=12345, text="Привет"):
        self.from_id = from_id
        self.text = text
        self.answer = AsyncMock()


class MockEventObject:
    """Мок для данных внутри Callback-события"""

    def __init__(self, user_id=12345, peer_id=12345, cmid=1):
        self.user_id = user_id
        self.peer_id = peer_id
        self.conversation_message_id = cmid


class MockEvent:
    """Мок для нажатия на инлайн-кнопку (GroupTypes.MessageEvent)"""

    def __init__(self, user_id=12345, payload=None):
        self.object = MockEventObject(user_id=user_id)
        self.payload = payload or {}

        # Мокаем API ВКонтакте
        self.ctx_api = MagicMock()
        self.ctx_api.messages.edit = AsyncMock()
        self.ctx_api.messages.send = AsyncMock()

        # Мокаем получение имени пользователя из ВК
        mock_user = MagicMock()
        mock_user.first_name = "Иван"
        mock_user.last_name = "Иванов"
        self.ctx_api.users.get = AsyncMock(return_value=[mock_user])


# === ТЕСТЫ ===
class VkBotDbUtilsTest(TestCase):
    """1. Тестирование утилит для работы с БД (vk_bot/utils/db.py)"""

    def setUp(self):
        UserRole.objects.create(name='Участник')

    def test_create_and_get_user(self):
        """Проверка безопасного создания пользователя и профиля с VK ID"""
        vk_id = 999888
        async_to_sync(create_user_and_profile)(
            username=f"vk_{vk_id}",
            password="123",
            first_name="Тест",
            last_name="Тестов",
            vk_id=vk_id
        )
        self.assertTrue(User.objects.filter(username=f"vk_{vk_id}").exists())
        user = async_to_sync(get_current_user)(vk_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "Тест")

    def test_get_user_stats(self):
        """Проверка подсчета статистики игр для профиля"""
        user = User.objects.create_user(username='stat_user', password='123')
        user.profile.vk_id = 111222
        user.profile.save()

        q_set = QuizQuestionSet.objects.create(name="Тестовый набор", owner=user)
        # Создаем две разные игры
        game1 = QuizGame.objects.create(owner=user, question_set=q_set, name="Game 1", game_code="AAAA")
        game2 = QuizGame.objects.create(owner=user, question_set=q_set, name="Game 2", game_code="BBBB")

        GameResult.objects.create(game=game1, player=user, score=100)
        GameResult.objects.create(game=game2, player=user, score=50)

        games_played, total_score = async_to_sync(get_user_stats)(user)
        self.assertEqual(games_played, 2)
        self.assertEqual(total_score, 150)


class VkBotStatesTest(TestCase):
    """2. Тестирование Redis состояний пользователя (FSM)"""

    @patch('vk_bot.utils.states.redis_client')
    def test_state_management(self, mock_redis):
        """Проверка установки и сброса состояний"""
        vk_id = 12345
        mock_redis.get.return_value = UserState.WAITING_FOR_CODE.value

        state = async_to_sync(get_state)(vk_id)
        self.assertEqual(state, UserState.WAITING_FOR_CODE.value)

        async_to_sync(set_state)(vk_id, UserState.WAITING_FOR_CODE)

        save_called = any(call[0] in ['set', 'setex'] for call in mock_redis.method_calls)
        self.assertTrue(save_called, "Метод сохранения в Redis не был вызван")

        async_to_sync(clear_state)(vk_id)
        mock_redis.delete.assert_called_once_with(f"vk_bot:state:{vk_id}")


class VkBotHandlersTest(TestCase):
    """3. Тестирование логики команд и кнопок (Handlers)"""

    def setUp(self):
        UserRole.objects.create(name='Участник')

    @patch('vk_bot.utils.db.get_current_user')
    @patch('vk_bot.utils.states.get_state')
    def test_start_handler_new_user(self, mock_get_state, mock_get_user):
        """Тест команды 'Начать' для НОВОГО пользователя"""
        mock_get_user.return_value = None
        mock_get_state.return_value = None

        message = MockMessage(from_id=111)
        async_to_sync(start_command)(message)

        # Проверяем, что бот попытался ответить
        self.assertTrue(message.answer.called)

    @patch('vk_bot.handlers.callback_handlers.game_callback_handler.set_state')
    def test_join_game_callback(self, mock_set_state):
        """Тест кнопки 'Присоединиться к игре'"""
        user = User.objects.create_user(username='player', password='123')
        user.profile.vk_id = 777
        user.profile.save()

        event = MockEvent(user_id=777)
        async_to_sync(join_game)(event)

        mock_set_state.assert_called_once_with(777, UserState.WAITING_FOR_CODE)

        message_sent = event.ctx_api.messages.edit.called or event.ctx_api.messages.send.called
        self.assertTrue(message_sent, "Сообщение не было отправлено или отредактировано")

    def test_create_profile_callback(self):
        """Тест инлайн-кнопки 'Создать профиль'"""
        vk_id = 555444
        event = MockEvent(user_id=vk_id)

        async_to_sync(create_profile)(event)

        # Проверяем вызов VK API
        event.ctx_api.users.get.assert_called_once_with(user_ids=[vk_id])

        user = async_to_sync(get_current_user)(vk_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "Иван")

        message_sent = event.ctx_api.messages.edit.called or event.ctx_api.messages.send.called
        self.assertTrue(message_sent, "Сообщение об успехе не было отправлено")
