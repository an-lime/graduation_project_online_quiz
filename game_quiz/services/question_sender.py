import requests
from typing import List, Dict
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class VKQuestionSender:
    """Отправка вопросов через VK Bot API"""

    def __init__(self):
        self.bot_token = getattr(settings, 'VK_BOT_TOKEN', None)
        self.api_version = '5.199'
        self.base_url = 'https://api.vk.com/method'

    def send_question_to_users(
            self,
            participants: List[Dict],
            question_text: str,
            options: List[str],
            game_code: str
    ) -> Dict:
        """
        Отправить вопрос всем участникам

        participants: [{'vk_id': 123, 'username': 'test'}, ...]
        """
        if not self.bot_token:
            logger.error("VK_BOT_TOKEN not configured")
            return {'success': False, 'error': 'Bot token not configured'}

        success_count = 0
        failed_users = []

        for participant in participants:
            try:
                self._send_message_with_keyboard(
                    peer_id=participant['vk_id'],
                    message=f"❓ {question_text}",
                    options=options,
                    game_code=game_code
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {participant['username']}: {e}")
                failed_users.append(participant['username'])

        return {
            'success': success_count > 0,
            'sent': success_count,
            'failed': failed_users
        }

    def _send_message_with_keyboard(
            self,
            peer_id: int,
            message: str,
            options: List[str],
            game_code: str
    ):
        """Отправить сообщение с inline-клавиатурой"""
        import json

        # Создаём клавиатуру
        keyboard = {
            "inline": True,
            "buttons": []
        }

        # Добавляем кнопки по 2 в ряд
        for i in range(0, len(options), 2):
            row = []
            for j in range(2):
                idx = i + j
                if idx < len(options):
                    row.append({
                        "action": {
                            "type": "callback",
                            "label": options[idx],
                            "payload": json.dumps({
                                "action": "answer",
                                "game_code": game_code,
                                "option_index": idx
                            })
                        }
                    })
            keyboard["buttons"].append(row)

        # Отправляем сообщение
        response = requests.post(
            f"{self.base_url}/messages.send",
            data={
                'peer_id': peer_id,
                'message': message,
                'keyboard': json.dumps(keyboard),
                'random_id': 0,
                'access_token': self.bot_token,
                'v': self.api_version
            },
            timeout=5
        )

        result = response.json()
        if 'error' in result:
            raise Exception(f"VK API error: {result['error']}")
