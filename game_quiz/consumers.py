import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from game_quiz.models import QuizGame, GameParticipant
from game_quiz.services.game_session import get_game_session
from game_quiz.services.question_sender import VKQuestionSender

logger = logging.getLogger(__name__)


class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"🔌 [WS] Connect attempt: {self.scope['path']}")

        try:
            # 1. Получаем код игры
            self.game_code = self.scope['url_route']['kwargs']['game_code'].upper()
            self.room_group_name = f'lobby_{self.game_code}'
            print(f"🔍 [WS] Checking game: {self.game_code}")

            # 2. Проверка существования игры (БД запрос)
            if not await self.check_game_exists():
                print(f"❌ [WS] Game {self.game_code} not found")
                await self.close()
                return

            # 3. Присоединяемся к группе каналов
            print(f"✅ [WS] Adding to group: {self.room_group_name}")
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # 4. ⚠️ КРИТИЧНО: Принимаем соединение (должно быть ВЫЗВАНО)
            print(f"🤝 [WS] Accepting connection")
            await self.accept()

            # 5. Отправляем начальный список участников
            participants = await self.get_participants()
            await self.send(text_data=json.dumps({
                'type': 'participants_list',
                'participants': participants
            }))
            print(f"📤 [WS] Sent initial list")

        except Exception as e:
            # Ловим любую ошибку, чтобы увидеть её в консоли
            print(f"💥 [WS] ERROR in connect: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await self.close()
            except:
                pass

    async def disconnect(self, close_code):
        print(f"🔌 [WS] Disconnect: {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    @database_sync_to_async
    def check_game_exists(self):
        return QuizGame.objects.filter(game_code=self.game_code).exists()

    @database_sync_to_async
    def get_participants(self):
        participants = GameParticipant.objects.filter(
            game__game_code=self.game_code
        ).select_related('player', 'game__owner')
        return [
            {'username': p.player.username, 'is_host': p.player.id == p.game.owner.id}
            for p in participants
        ]

    # === Обработчики событий ===
    async def participant_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'username': event['username'],
            'is_host': event.get('is_host', False)
        }))

    async def participant_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_left',
            'username': event['username']
        }))


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_code = self.scope['url_route']['kwargs']['game_code'].upper()
        self.room_group_name = f'game_{self.game_code}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        session = get_game_session(self.game_code)

        if action == 'start_game':
            success = await session.start_game()  # ✅ await
            if success:
                question_data = await session.next_question()  # ✅ await
                if question_data:
                    await self._send_question(session, question_data)

        elif action == 'next_question':
            question_data = await session.next_question()  # ✅ await
            if question_data:
                await self._send_question(session, question_data)
            else:
                await self.send(text_data=json.dumps({'type': 'game_ended'}))

    async def _send_question(self, session, question_data):

        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'question_update', **question_data}
        )

        participants = session.get_participants_for_bot()
        if participants:
            sender = VKQuestionSender()
            sender.send_question_to_users(
                participants=participants,
                question_text=question_data['text'],
                options=question_data['options'],
                game_code=self.game_code
            )

    async def game_started(self, event):
        await self.send(text_data=json.dumps({'type': 'game_started'}))

    async def question_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def timer_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def player_answer(self, event):
        await self.send(text_data=json.dumps(event))

    async def leaderboard_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def question_ended(self, event):
        await self.send(text_data=json.dumps(event))

    async def game_ended(self, event):
        await self.send(text_data=json.dumps({'type': 'game_ended'}))
