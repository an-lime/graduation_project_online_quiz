# game_quiz/services/game_session.py

import asyncio
import json
import logging

import redis
from asgiref.sync import sync_to_async, async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils import timezone

from game_quiz.models import QuizGame, GameParticipant, GameResult

User = get_user_model()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
logger = logging.getLogger(__name__)


class GameSession:
    REDIS_TTL = 7200  # 2 часа

    def __init__(self, game_code: str):
        self.game_code = game_code.upper()
        self.redis_key = f"game_session:{self.game_code}"
        self.channel_layer = get_channel_layer()
        self._timer_task = None

    def get_state(self):
        """Получение состояния из Redis"""
        data = redis_client.get(self.redis_key)
        return json.loads(data) if data else None

    def save_state(self, state):
        """Сохранение состояния в Redis"""
        redis_client.setex(self.redis_key, self.REDIS_TTL, json.dumps(state))

    async def start_game(self) -> bool:
        """Запуск новой игры"""
        try:
            game = await sync_to_async(
                lambda: QuizGame.objects.select_related('owner', 'question_set').get(
                    game_code=self.game_code
                )
            )()

            if game.status != 'waiting':
                logger.warning(f"Game {self.game_code} status is {game.status}, not waiting")
                return False

            participants_qs = await sync_to_async(
                lambda: list(
                    GameParticipant.objects.filter(game=game)
                    .select_related('player__profile')
                    .values(
                        'player__username',
                        'player__first_name',
                        'player__last_name',
                        'player__profile__vk_id'
                    )
                )
            )()

            logger.info(f"Starting game {self.game_code} with {len(participants_qs)} participants")

            state = {
                'game_id': game.id,
                'game_name': game.name,
                'host_username': game.owner.username,
                'questions': game.question_set.quiz_set_content,
                'current_idx': -1,
                'timer_seconds': 30,
                'is_running': True,
                'started_at': timezone.now().isoformat(),
                'participants': {
                    p['player__profile__vk_id']: {
                        'username': p['player__username'],
                        'first_name': p['player__first_name'],
                        'last_name': p['player__last_name'],
                        'vk_id': p['player__profile__vk_id'],
                        'score': 0,
                        'correct': 0,
                        'correct_count': 0,
                        'total': 0,
                        'answered_current': False,
                        'answer_time': 0,
                        'is_host': p['player__username'] == game.owner.username
                    } for p in participants_qs
                }
            }

            self.save_state(state)

            await sync_to_async(
                lambda: QuizGame.objects.filter(id=game.id).update(
                    status='playing',
                    started_at=timezone.now()
                )
            )()

            await self.channel_layer.group_send(
                f'game_{self.game_code}', {'type': 'game_started'}
            )
            logger.info(f"Game {self.game_code} started successfully")
            return True

        except QuizGame.DoesNotExist:
            logger.error(f"Game {self.game_code} not found")
            return False
        except Exception as e:
            logger.error(f"Error in start_game: {e}", exc_info=True)
            return False

    async def next_question(self):
        """Загружает следующий вопрос и возвращает данные для отправки"""
        logger.info(f"📥 next_question() called for {self.game_code}")

        state = self.get_state()
        if not state or not state.get('is_running'):
            logger.error(f"❌ No state or not running for {self.game_code}")
            return None

        state['current_idx'] += 1
        logger.info(f"📊 Current index: {state['current_idx']}, Total: {len(state['questions'])}")

        if state['current_idx'] >= len(state['questions']):
            logger.info(f"🏁 All questions answered, ending game")
            await self.end_game()
            return None

        # Сброс статусов для нового вопроса
        for vk_id in state['participants']:
            state['participants'][vk_id]['answered_current'] = False
            state['participants'][vk_id]['answer_time'] = 0

        state['question_active'] = True
        self.save_state(state)

        question = state['questions'][state['current_idx']]

        asyncio.create_task(self._start_timer())

        # ✅ ВОЗВРАЩАЕМ correct_index И explanation
        return {
            'question_number': state['current_idx'] + 1,
            'total_questions': len(state['questions']),
            'text': question['question'],
            'options': question.get('options') or question.get('answers') or [],
            'correct_index': question.get('correctIndex') or question.get('correct_answer') or -1,
            'explanation': question.get('explanation') or question.get('hint') or '',
            'timer': state['timer_seconds']
        }

    def handle_answer(self, vk_id: int, option_index: int) -> dict:
        """Обработка ответа игрока (sync-метод)"""
        state = self.get_state()
        if not state:
            return {'success': False, 'error': 'Game not found'}

        if not state.get('question_active'):
            return {'success': False, 'error': 'Question already ended'}

        vk_id_str = str(vk_id)

        if vk_id_str not in state['participants']:
            logger.warning(f"Player {vk_id} not found in participants. Available: {list(state['participants'].keys())}")
            return {'success': False, 'error': 'Player not in game'}

        player = state['participants'][vk_id_str]

        if player['answered_current']:
            return {'success': False, 'error': 'Already answered'}

        question = state['questions'][state['current_idx']]
        correct_index = question.get('correctIndex', -1)
        is_correct = option_index == correct_index

        # Обновляем статистику
        player['answered_current'] = True
        player['correct'] = is_correct
        player['answer_time'] = state['timer_seconds']

        if is_correct:
            speed_bonus = max(0, (state['timer_seconds'] - player['answer_time']) * 5)
            player['score'] += 100 + speed_bonus
            player['correct_count'] = player.get('correct_count', 0) + 1
        player['total'] += 1

        self.save_state(state)

        # Отправляем событие на сайт
        async_to_sync(self.channel_layer.group_send)(
            f'game_{self.game_code}',
            {
                'type': 'player_answer',
                'vk_id': vk_id,
                'username': player['username'],
                'correct': is_correct
            }
        )

        # ✅ ПРОВЕРКА: все ли игроки ответили?
        if self._check_all_answered(state):
            logger.info(f"✅ All players answered, finishing question early")
            async_to_sync(self._finish_question)()

        return {'success': True, 'correct': is_correct}

    def _check_all_answered(self, state) -> bool:
        """Проверяет, ответили ли все реальные игроки (не ведущий)"""
        for p in state['participants'].values():
            # Пропускаем ведущего и тех, у кого нет vk_id
            if p.get('is_host', False) or not p['vk_id']:
                continue
            if not p['answered_current']:
                return False
        return True

    async def _start_timer(self):
        """Запускает обратный отсчёт"""
        try:
            state = self.get_state()
            if not state:
                logger.warning(f"No state for timer in {self.game_code}")
                return

            remaining = state['timer_seconds']

            while remaining >= 0 and state.get('question_active'):
                await self.channel_layer.group_send(
                    f'game_{self.game_code}',
                    {'type': 'timer_update', 'seconds_left': remaining}
                )

                if remaining == 0:
                    logger.info(f"⏱ Timer expired for {self.game_code}")
                    await self._finish_question(timer_ended=True)
                    break

                await asyncio.sleep(1)
                remaining -= 1
                # ✅ Обновляем состояние на случай изменений
                state = self.get_state()
                if not state:
                    break

        except Exception as e:
            logger.error(f"Error in timer for {self.game_code}: {e}", exc_info=True)

    async def _stop_timer(self):
        """Останавливает активный таймер"""
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

    async def _finish_question(self, timer_ended=False):

        print('Вопрос завершён')
        """Завершает вопрос: сохраняет результаты, шлёт финальные события"""
        state = self.get_state()
        if not state or not state.get('question_active'):
            return

        state['question_active'] = False

        if timer_ended:
            print('Не ответили за время: ')
            for k, v in state['participants'].items():
                if not v['answered_current']:
                    print(v['username'])

        print('__________________________________')

        print('Ответили за время: ')
        for k, v in state['participants'].items():
            if v['answered_current']:
                print(v['username'])

        self.save_state(state)

        # Сохраняем результаты (не прерываемся при ошибке)
        try:
            await self._save_results_to_db(state)
            await self._broadcast_leaderboard(state)
        except Exception as e:
            logger.error(f"Warning: Failed to save results: {e}")

        # ✅ ОТПРАВЛЯЕМ question_ended ВСЕГДА (даже если БД упала)
        question = state['questions'][state['current_idx']]
        await self.channel_layer.group_send(
            f'game_{self.game_code}',
            {
                'type': 'question_ended',
                'correct_index': question.get('correctIndex') or question.get('correct_answer') or -1,
                'explanation': question.get('explanation') or question.get('hint') or '',
                'options': question.get('options') or question.get('answers') or []
            }
        )

    async def end_game(self):
        """Полное завершение игры"""
        state = self.get_state()
        if not state:
            return

        await self._stop_timer()

        try:
            await self._save_results_to_db(state)

            await sync_to_async(
                lambda: QuizGame.objects.filter(game_code=self.game_code).update(
                    status='finished', finished_at=timezone.now()
                )
            )()

            # Исключаем ведущего из результатов
            sorted_players = sorted(
                [p for p in state['participants'].values() if not p.get('is_host', False)],
                key=lambda x: x['score'],
                reverse=True
            )

            final_results = [
                {
                    'rank': i + 1,
                    'name': f"{p['first_name']} {p['last_name']}" if p['first_name'] else p['username'],
                    'username': p['username'],
                    'score': p['score'],
                    'correct': p.get('correct_count', 0),
                    'total': p['total'],
                    'is_host': p.get('is_host', False)
                }
                for i, p in enumerate(sorted_players)
            ]

            await self.channel_layer.group_send(
                f'game_{self.game_code}',
                {
                    'type': 'game_ended',
                    'results': final_results,
                    'total_questions': len(state['questions']),
                    'game_name': state.get('game_name', 'Викторина')
                }
            )

        finally:
            redis_client.delete(self.redis_key)

    async def _save_results_to_db(self, state):
        """Сохраняет статистику игроков в БД"""
        try:
            game_id = state['game_id']

            for vk_id, data in state['participants'].items():
                username = data.get('username')

                if not username:
                    logger.warning(f"No username for participant {vk_id}")
                    continue

                # Сначала получаем пользователя
                user = await sync_to_async(
                    lambda u=username: User.objects.get(username=u)
                )()

                # ✅ ИСПРАВЛЕНО: правильно передаём data в lambda
                await sync_to_async(
                    lambda u=user, d=data: GameResult.objects.update_or_create(
                        game_id=game_id,
                        player=u,
                        defaults={
                            'score': d['score']
                        }
                    )
                )()

            logger.info(f"Results saved for game {game_id}")

        except Exception as e:
            logger.error(f"Error saving results: {e}")

    async def _broadcast_leaderboard(self, state):
        """Рассылает текущий рейтинг всем подключенным"""
        # Исключаем ведущего из рейтинга
        sorted_players = sorted(
            [p for p in state['participants'].values() if not p.get('is_host', False)],
            key=lambda x: x['score'],
            reverse=True
        )

        leaderboard = [
            {
                'name': f"{p['first_name']} {p['last_name']}" if p['first_name'] else p['username'],
                'score': p['score'],
                'correct': p.get('correct_count', 0),
                'total': p['total']
            }
            for p in sorted_players
        ]

        await self.channel_layer.group_send(
            f'game_{self.game_code}',
            {'type': 'leaderboard_update', 'leaderboard': leaderboard}
        )

    def get_participants_for_bot(self):
        """Возвращает список участников для рассылки (без ведущего)"""
        state = self.get_state()
        if not state:
            return []

        host_username = state.get('host_username')
        return [
            {
                'vk_id': p['vk_id'],
                'username': p['username'],
                'name': f"{p['first_name']} {p['last_name']}" if p['first_name'] else p['username']
            }
            for p in state['participants'].values()
            if p['vk_id'] and p['username'] != host_username
        ]


def get_game_session(game_code: str) -> GameSession:
    """Factory function"""
    return GameSession(game_code)
