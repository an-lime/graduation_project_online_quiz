import json
import logging
from typing import List, Dict

import requests
import vk_api
from django.conf import settings

from game_quiz.services.game_session import redis_client
from vk_bot.utils.support_functions import generate_event_random_id

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
    ):
        """
        Отправить вопрос всем участникам

        participants: [{'vk_id': 123, 'username': 'test'}, ...]
        """
        if not self.bot_token:
            logger.error("VK_BOT_TOKEN not configured")
            return {'success': False, 'error': 'Bot token not configured'}

        for participant in participants:
            self._send_message_with_keyboard(
                peer_id=participant['vk_id'],
                message=f"❓ {question_text}",
                options=options,
                game_code=game_code
            )

            # try:
            #     self._send_message_with_keyboard(
            #         peer_id=participant['vk_id'],
            #         message=f"❓ {question_text}",
            #         options=options,
            #         game_code=game_code
            #     )
            # except Exception as e:
            #     logger.error(f"Failed to send to {participant['username']}: {e}")

        return None

    def _send_message_with_keyboard(
            self,
            peer_id: int,
            message: str,
            options: List[str],
            game_code: str,
    ):
        """Отправить сообщение с inline-клавиатурой"""

        redis_key = f"game_session:{game_code}"

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

        print('peer: ', peer_id)
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
        state = json.loads(redis_client.get(redis_key))

        vk = vk_api.VkApi(token=self.bot_token)
        message_info = vk.method("messages.getById", {
            "message_ids": [result["response"]]
        })

        if message_info["count"] > 0:
            state['participants'][str(peer_id)]['cmid'] = message_info["items"][0]["conversation_message_id"]

        if 'error' in result:
            raise Exception(f"VK API error: {result['error']}")
