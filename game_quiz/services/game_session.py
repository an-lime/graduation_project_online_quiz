import asyncio
import json
import logging

import redis
import vk_api
from asgiref.sync import sync_to_async, async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from game_quiz.models import QuizGame, GameParticipant, GameResult
from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.utils.support_functions import generate_event_random_id

User = get_user_model()
# Клиент Redis для хранения состояния игровой сессии
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
logger = logging.getLogger(__name__)


class GameSession:
    """
    Класс управления игровой сессией викторины.

    Отвечает за хранение состояния игры в Redis, управление таймером,
    обработку ответов игроков и рассылку событий через WebSocket.

    Attributes:
        REDIS_TTL - Время жизни сессии в Redis (из настроек Django)
        game_code - Код комнаты (приведённый к верхнему регистру)
        redis_key - Ключ для хранения состояния в Redis
        channel_layer - Слой каналов Django для WebSocket коммуникации
        _timer_task - Задача асинхронного таймера
        bot_token - Токен VK бота
        vk - Инициализированный клиент VK API
    """
    REDIS_TTL = getattr(settings, 'REDIS_TTL', None)

    def __init__(self, game_code: str):
        """
        Инициализация игровой сессии.

        Args:
            game_code: Уникальный код комнаты (4 символа)
        """
        self.game_code = game_code.upper()
        self.redis_key = f"game_session:{self.game_code}"
        self.channel_layer = get_channel_layer()
        self._timer_task = None
        self.bot_token = getattr(settings, 'VK_BOT_TOKEN', None)
        self.vk = vk_api.VkApi(token=self.bot_token)

    def get_state(self):
        """
        Получение текущего состояния игры из Redis.

        Returns:
            dict: Словарь с данными состояния или None если сессия не найдена
        """
        """Получение состояния из Redis"""
        data = redis_client.get(self.redis_key)
        return json.loads(data) if data else None

    def save_state(self, state):
        """
        Сохранение состояния игры в Redis с установленным TTL.

        Args:
            state: Словарь с данными состояния игры
        """
        """Сохранение состояния в Redis"""
        redis_client.setex(self.redis_key, self.REDIS_TTL, json.dumps(state))

    async def start_game(self) -> bool:
        """
        Запуск новой игровой сессии.

        Инициализирует состояние игры в Redis, загружает данные участников
        и рассылает уведомление о начале игры через WebSocket.

        Returns:
            bool: True если игра успешно запущена, False иначе

        Raises:
            QuizGame.DoesNotExist: Если игра с указанным кодом не найдена

        Note:
            - Блокирует запуск если игра уже завершена (status='finished')
            - Защищает от повторного запуска активной сессии
        """
        """Запуск новой игры"""
        try:
            game = await sync_to_async(
                lambda: QuizGame.objects.select_related('owner', 'question_set').get(
                    game_code=self.game_code
                )
            )()

            # Так как мы меняем статус на 'playing' при входе в игру,
            # блокируем старт только если игра уже 'finished'
            if game.status == 'finished':
                logger.warning(f"Game {self.game_code} status is already {game.status}")
                return False

            # Защита от двойного нажатия: проверяем, не запущена ли уже сессия в Redis
            existing_state = self.get_state()
            if existing_state and existing_state.get('is_running'):
                logger.warning(f"Game {self.game_code} is already running in Redis")
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
                'timer_seconds': 20,
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
        """
        Загрузка следующего вопроса и подготовка данных для отправки.

        Увеличивает индекс текущего вопроса, сбрасывает флаги ответов участников
        и запускает таймер обратного отсчёта.

        Returns:
            dict: Словарь с данными вопроса или None если вопросы закончились

        Context:
            question_number - Номер текущего вопроса (1-based)
            total_questions - Общее количество вопросов в игре
            text - Текст вопроса
            options - Список вариантов ответа
            correct_index - Индекс правильного ответа
            explanation - Пояснение к ответу
            timer - Время на ответ в секундах

        Note:
            Если вопросы закончились, автоматически вызывает end_game()
        """
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

        for vk_id in state['participants']:
            state['participants'][vk_id]['answered_current'] = False
            state['participants'][vk_id]['answer_time'] = 0

        state['question_active'] = True
        self.save_state(state)

        question = state['questions'][state['current_idx']]

        asyncio.create_task(self._start_timer())

        return {
            'question_number': state['current_idx'] + 1,
            'total_questions': len(state['questions']),
            'text': question['question'],
            'options': question.get('options') or question.get('answers') or [],
            'correct_index': question.get('correctIndex') if question.get('correctIndex') is not None else question.get(
                'correct_answer', -1),
            'explanation': question.get('explanation') or question.get('hint') or '',
            'timer': state['timer_seconds']
        }

    def handle_answer(self, vk_id: int, option_index: int) -> dict:
        """
        Обработка ответа игрока на текущий вопрос.

        Проверяет правильность ответа, обновляет статистику игрока
        и рассылает событие через WebSocket. Если все игроки ответили,
        досрочно завершает вопрос.

        Args:
            vk_id: ID пользователя VK
            option_index: Индекс выбранного варианта ответа

        Returns:
            dict: Результат обработки {'success': bool, 'correct': bool, 'error': str}

        Note:
            Синхронный метод, вызывается из Django view
        """
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

        if is_correct:
            player['score'] += 10
            player['correct_count'] = player.get('correct_count', 0) + 1
        player['total'] += 1

        # Обновляем статистику
        player['answered_current'] = True
        player['correct'] = is_correct
        player['answer_time'] = state['timer_seconds']

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
            if not p['vk_id']:
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

            # 1. Получаем текст вопроса и варианты ответов
            current_question = state['questions'][state['current_idx']]
            question_text = current_question.get('question', 'Вопрос')
            options = current_question.get('options') or current_question.get('answers') or []

            # 2. Заново собираем inline-клавиатуру
            keyboard = {"inline": True, "buttons": []}
            for i in range(0, len(options), 2):
                row = []
                for j in range(2):
                    idx = i + j
                    if idx < len(options):
                        row.append({
                            "action": {
                                "type": "callback",
                                "label": str(options[idx]),
                                "payload": json.dumps({
                                    "action": "answer",
                                    "game_code": self.game_code,
                                    "option_index": idx
                                })
                            }
                        })
                keyboard["buttons"].append(row)

            keyboard_json = json.dumps(keyboard)

            while remaining >= 0 and state.get('question_active'):
                await self.channel_layer.group_send(
                    f'game_{self.game_code}',
                    {'type': 'timer_update', 'seconds_left': remaining}
                )

                # 3. Редактируем сообщение, обязательно передавая keyboard
                if remaining == 10:
                    for k, v in state['participants'].items():
                        if not v.get('is_host') and not v.get('answered_current') and v.get('cmid'):
                            try:
                                self.vk.method("messages.edit", {
                                    "peer_id": v['vk_id'],
                                    "cmid": v['cmid'],
                                    "message": f"❓ {question_text}\n\n⏳ Осталось 10 секунд!",
                                    "keyboard": keyboard_json  # <--- Возвращаем клавиатуру на место
                                })
                            except Exception as e:
                                logger.error(f"Ошибка добавления 10 секунд для {v.get('vk_id')}: {e}")

                if remaining == 0:
                    logger.info(f"⏱ Timer expired for {self.game_code}")
                    await self._finish_question(timer_ended=True)
                    break

                await asyncio.sleep(1)
                remaining -= 1
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
        """Завершает вопрос: сохраняет результаты, шлёт финальные события"""

        state = self.get_state()
        if not state or not state.get('question_active'):
            return

        state['question_active'] = False

        if timer_ended:
            for k, v in state['participants'].items():
                if not v['answered_current'] and not v['is_host']:
                    try:
                        self.vk.method("messages.edit", {
                            "peer_id": v['vk_id'],
                            "cmid": v['cmid'],
                            "message": 'Время вышло!',
                        })
                    except Exception as e:
                        logger.error(f"Ошибка изменения сообщения ВК для vk_id {v.get('vk_id')}: {e}")

        self.save_state(state)

        # Сохраняем результаты (не прерываемся при ошибке)
        try:
            await self._save_results_to_db(state)
            await self._broadcast_leaderboard(state)
        except Exception as e:
            logger.error(f"Warning: Failed to save results: {e}")

        # ✅ ОТПРАВЛЯЕМ question_ended ВСЕГДА (даже если БД упала)
        question = state['questions'][state['current_idx']]
        is_last = state['current_idx'] == len(state['questions']) - 1

        await self.channel_layer.group_send(
            f'game_{self.game_code}',
            {
                'type': 'question_ended',
                'correct_index': question.get('correctIndex') if question.get(
                    'correctIndex') is not None else question.get('correct_answer', -1),
                'explanation': question.get('explanation') or question.get('hint') or '',
                'options': question.get('options') or question.get('answers') or [],
                'is_last': is_last
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

            await sync_to_async(
                lambda: GameParticipant.objects.filter(game__game_code=self.game_code).delete()
            )()

            # Исключаем ведущего из результатов
            sorted_players = sorted(
                [p for p in state['participants'].values() if not p.get('is_host', False)],
                key=lambda x: x['score'],
                reverse=True
            )

            main_menu_kb = create_main_menu_keyboard()

            final_results = [
                {
                    'rank': i + 1,
                    'name': f"{p['first_name']} {p['last_name']}" if p['first_name'] else p['username'],
                    'username': p['username'],
                    'score': p['score'],
                    'correct': p.get('correct_count', 0),
                    'total': p['total'],
                    'is_host': p.get('is_host', False),
                    'vk_id': p['vk_id']  # <-- Убедись, что vk_id прокидывается для бота
                }
                for i, p in enumerate(sorted_players)
            ]

            for player in final_results:
                if player.get('vk_id'):
                    msg = (
                        f"🏁 Игра «{state.get('game_name', 'Викторина')}» завершена!\n\n"
                        f"🏆 Вы заняли {player['rank']} место.\n"
                        f"🎯 Правильных ответов: {player['correct']} из {player['total']}\n"
                        f"⭐ Набрано очков: {player['score']}"
                    )
                    try:
                        self.vk.method("messages.send", {
                            "peer_id": player['vk_id'],
                            "random_id": generate_event_random_id(),
                            "message": msg,
                            "keyboard": main_menu_kb
                        })
                    except Exception as e:
                        logger.error(f"Ошибка отправки результата игроку {player['vk_id']}: {e}")

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

            # 1. Вычисляем текущие места игроков
            # Исключаем ведущего и сортируем по очкам (по убыванию)
            sorted_players = sorted(
                [p for p in state['participants'].values() if not p.get('is_host', False)],
                key=lambda x: x['score'],
                reverse=True
            )

            # 2. Создаем словарь для быстрого получения ранга по username
            ranks = {player['username']: index + 1 for index, player in enumerate(sorted_players)}

            for vk_id, data in state['participants'].items():

                if data.get('is_host', False):
                    continue

                username = data.get('username')

                if not username:
                    logger.warning(f"No username for participant {vk_id}")
                    continue

                # Находим место конкретного игрока
                player_rank = ranks.get(username)

                # Сначала получаем пользователя
                user = await sync_to_async(
                    lambda u=username: User.objects.get(username=u)
                )()

                # 3. Добавляем сохранение 'rank' в defaults
                await sync_to_async(
                    lambda u=user, d=data, r=player_rank: GameResult.objects.update_or_create(
                        game_id=game_id,
                        player=u,
                        defaults={
                            'score': d['score'],
                            'rank': r
                        }
                    )
                )()

            logger.info(f"Results and ranks saved for game {game_id}")

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

    async def remove_player(self, vk_id: int) -> bool:
        """Асинхронный метод для корректного удаления игрока из сессии"""
        state = self.get_state()

        # УБИРАЕМ ПРОВЕРКУ `not state.get('is_running')`,
        # потому что игроки могут выйти ДО нажатия кнопки "Старт"
        if not state:
            return False

        vk_id_str = str(vk_id)
        if vk_id_str in state.get('participants', {}):
            # 1. Удаляем игрока из словаря
            del state['participants'][vk_id_str]
            self.save_state(state)
            logger.info(f"🚪 Игрок {vk_id_str} удален из сессии {self.game_code}")

            # 2. Ищем, остались ли НЕ ведущие (обычные игроки)
            players_left = [p for p in state['participants'].values() if not p.get('is_host')]

            if not players_left:
                # Никого не осталось — прерываем и удаляем игру даже до старта!
                logger.info(f"🛑 Все игроки покинули игру {self.game_code}. Отмена игры.")
                await self._abort_game()
                return True

            # 3. Если идет вопрос (И игра уже была запущена), проверяем таймер
            if state.get('is_running') and state.get('question_active'):
                if self._check_all_answered(state):
                    logger.info(f"✅ Вышедший игрок был последним неответившим. Досрочно завершаем вопрос.")
                    await self._finish_question()

            return True
        return False

    async def _abort_game(self):
        """Полностью удаляет игру и рассылает сигнал об отмене"""
        from asgiref.sync import sync_to_async
        from game_quiz.models import QuizGame

        state = self.get_state()
        if state:
            await self._stop_timer()
            # Очищаем Redis
            redis_client.delete(self.redis_key)

        # Удаляем игру из базы данных (каскадно удалятся участники и результаты)
        await sync_to_async(
            lambda: QuizGame.objects.filter(game_code=self.game_code).delete()
        )()

        # Отправляем сигнал отмены в WebSocket для браузера
        await self.channel_layer.group_send(
            f'game_{self.game_code}',
            {'type': 'game_aborted'}
        )


def get_game_session(game_code: str) -> GameSession:
    """Factory function"""
    return GameSession(game_code)
