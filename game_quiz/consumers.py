import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from game_quiz.models import QuizGame, GameParticipant, GameResult
from game_quiz.services.game_session import get_game_session
from game_quiz.services.question_sender import VKQuestionSender

logger = logging.getLogger(__name__)


class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"🔌 [WS] Connect attempt: {self.scope['path']}")

        try:
            self.game_code = self.scope['url_route']['kwargs']['game_code'].upper()
            self.room_group_name = f'lobby_{self.game_code}'
            logger.info(f"🔍 [WS] Checking game: {self.game_code}")

            if not await self.check_game_exists():
                logger.warning(f"❌ [WS] Game {self.game_code} not found")
                await self.close()
                return

            logger.info(f"✅ [WS] Adding to group: {self.room_group_name}")
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            logger.info(f"🤝 [WS] Accepting connection")
            await self.accept()

            participants = await self.get_participants()
            await self.send(text_data=json.dumps({
                'type': 'participants_list',
                'participants': participants
            }))
            logger.info(f"📤 [WS] Sent initial list")

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

        # 1. Пытаемся восстановить текущую активную игру из Redis
        session = get_game_session(self.game_code)
        state = session.get_state()

        if state and state.get('is_running'):
            await self.send(text_data=json.dumps({
                'type': 'current_state',
                'state': state
            }))
        else:
            # 2. Если в Redis пусто, проверяем БД — возможно игра уже завершена
            finished_data = await self.get_finished_game_data()
            if finished_data:
                await self.send(text_data=json.dumps(finished_data))

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

    @database_sync_to_async
    def get_finished_game_data(self):
        """Получение данных уже завершенной игры для отображения итогов после перезагрузки"""
        try:
            from game_quiz.models import QuizGame, GameResult
            game = QuizGame.objects.get(game_code=self.game_code, status='finished')
            results_qs = GameResult.objects.filter(game=game).select_related('player').order_by('rank')

            results = []
            for r in results_qs:
                results.append({
                    'rank': r.rank or 0,
                    'name': f"{r.player.first_name} {r.player.last_name}" if r.player.first_name else r.player.username,
                    'score': r.score,
                    'correct': 0,
                    # В БД у нас сейчас не хранятся correct_count, можно оставить 0 или добавить поле в модель
                    'total': game.question_set.get_questions_count()
                })

            return {
                'type': 'game_ended',
                'results': results,
                'total_questions': game.question_set.get_questions_count(),
                'game_name': game.name
            }
        except Exception:
            return None

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
        await self.send(text_data=json.dumps(event))
