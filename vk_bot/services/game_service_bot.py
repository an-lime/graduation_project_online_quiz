import requests
import json
from typing import Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class GameAnswerHandler:
    """Обработка ответов игроков от VK бота"""

    def __init__(self):
        self.django_api_url = getattr(
            settings,
            'DJANGO_API_URL',
            'http://127.0.0.1:8000'
        )
        self.bot_token = getattr(settings, 'VK_BOT_TOKEN', None)

    async def handle_answer(
            self,
            user_id: int,
            game_code: str,
            option_index: int,
            conversation_message_id: Optional[int] = None
    ) -> bool:
        """
        Обработать ответ игрока

        Returns: True если ответ принят
        """
        # Получаем username из БД Django
        username = await self._get_username_by_vk_id(user_id)
        if not username:
            logger.warning(f"User {user_id} not found in database")
            return False

        # Отправляем ответ в Django
        try:
            response = requests.post(
                f"{self.django_api_url}/quiz/api/answer/",
                json={
                    'game_code': game_code,
                    'username': username,
                    'option_index': option_index
                },
                timeout=5
            )

            result = response.json()

            # Отправляем подтверждение игроку
            if result.get('success'):
                await self._send_confirmation(
                    user_id,
                    conversation_message_id,
                    correct=result.get('correct', False)
                )
                return True
            else:
                await self._send_error(user_id, conversation_message_id)
                return False

        except Exception as e:
            logger.error(f"Error sending answer to Django: {e}")
            return False

    async def _get_username_by_vk_id(self, vk_id: int) -> Optional[str]:
        """Получить username пользователя по VK ID"""
        try:
            # Запрос к Django API для получения username
            response = requests.get(
                f"{self.django_api_url}/bot_api/user/{vk_id}/",
                timeout=3
            )

            if response.status_code == 200:
                return response.json().get('username')
        except Exception as e:
            logger.error(f"Error getting username: {e}")

        return None

    async def _send_confirmation(
            self,
            user_id: int,
            cmid: Optional[int],
            correct: bool
    ):
        """Отправить подтверждение ответа"""
        if not self.bot_token:
            return

        message = "✅ Правильно!" if correct else "❌ Неправильно"

        try:
            if cmid:
                # Редактируем сообщение с вопросом
                requests.post(
                    'https://api.vk.com/method/messages.edit',
                    data={
                        'peer_id': user_id,
                        'cmid': cmid,
                        'message': f"{message}\n\nВаш ответ принят!",
                        'access_token': self.bot_token,
                        'v': '5.199'
                    },
                    timeout=3
                )
            else:
                # Отправляем новое сообщение
                requests.post(
                    'https://api.vk.com/method/messages.send',
                    data={
                        'peer_id': user_id,
                        'message': f"{message}\n\nВаш ответ принят!",
                        'random_id': 0,
                        'access_token': self.bot_token,
                        'v': '5.199'
                    },
                    timeout=3
                )
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")

    async def _send_error(self, user_id: int, cmid: Optional[int]):
        """Отправить сообщение об ошибке"""
        if not self.bot_token:
            return

        message = "⏱ Время вышло или ошибка!"

        try:
            if cmid:
                requests.post(
                    'https://api.vk.com/method/messages.edit',
                    data={
                        'peer_id': user_id,
                        'cmid': cmid,
                        'message': message,
                        'access_token': self.bot_token,
                        'v': '5.199'
                    },
                    timeout=3
                )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
