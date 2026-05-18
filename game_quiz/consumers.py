import json
import logging
import traceback

import requests
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

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


        elif data.get('action') == 'go_game_page':

            # Отправляем событие ВСЕМ в группе лобби
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'go_game_page'}
            )
            # ✅ ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ЧЕРЕЗ БОТА
            await self._notify_game_start_via_bot()

    @database_sync_to_async
    def get_game_and_participants(self):
        """Получает игру и участников для отправки уведомлений"""
        game = QuizGame.objects.select_related('owner').get(game_code=self.game_code)
        participants = GameParticipant.objects.filter(
            game=game
        ).select_related('player__profile')
        return game, [
            {
                'username': p.player.username,
                'vk_id': p.player.profile.vk_id if hasattr(p.player, 'profile') else None
            }
            for p in participants
        ]

    async def _notify_game_start_via_bot(self):
        """Отправляет уведомление о старте игры через бота"""
        bot_token = getattr(settings, 'VK_BOT_TOKEN', None)
        if not bot_token:
            logger.warning("VK_BOT_TOKEN not configured, skipping bot notifications")
            return

        try:
            game, participants = await self.get_game_and_participants()
            game_name = game.name

            for p in participants:
                vk_id = p.get('vk_id')
                username = p.get('username')

                if not vk_id:
                    logger.warning(f"No vk_id for participant {username}, skipping")
                    continue

                message = (
                    f"🎮 Игра \"{game_name}\" начинается!\n\n"
                    f"Следите за вопросами на экране трансляции. "
                    f"Удачи! 🍀"
                )

                try:
                    response = requests.post(
                        'https://api.vk.com/method/messages.send',
                        data={
                            'peer_id': vk_id,
                            'message': message,
                            'random_id': 0,
                            'access_token': bot_token,
                            'v': '5.199'
                        },
                        timeout=3
                    )

                    result = response.json()
                    if 'error' in result:
                        logger.error(f"VK API error: {result['error']}")
                    else:
                        logger.info(f"Sent start notification to {username} (vk_id={vk_id})")

                except Exception as e:
                    logger.error(f"Failed to send to {username}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to send bot notifications: {e}", exc_info=True)

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

    async def go_game_page(self, event):
        # Отправляем событие редиректа всем клиентам в лобби
        await self.send(text_data=json.dumps({
            'type': 'go_game_page'
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
