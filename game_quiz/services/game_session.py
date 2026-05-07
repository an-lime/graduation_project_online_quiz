import json

import redis
from asgiref.sync import sync_to_async, async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from game_quiz.models import QuizGame, GameParticipant, GameResult

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


class GameSession:
    REDIS_TTL = 7200

    def __init__(self, game_code: str):
        self.game_code = game_code.upper()
        self.redis_key = f"game_session:{self.game_code}"
        self.channel_layer = get_channel_layer()

    def get_state(self):
        data = redis_client.get(self.redis_key)
        return json.loads(data) if data else None

    def save_state(self, state):
        redis_client.setex(self.redis_key, self.REDIS_TTL, json.dumps(state))

    # ✅ ASYNC метод (вызывается из WebSocket потребителя)
    async def start_game(self) -> bool:
        try:
            # ✅ ДОБАВЛЕНО: select_related('owner', 'question_set')
            game = await sync_to_async(
                lambda: QuizGame.objects.select_related('owner', 'question_set').get(game_code=self.game_code)
            )()

            if game.status != 'waiting':
                return False

            # ✅ ДОБАВЛЕНО: select_related('player__profile')
            participants_qs = await sync_to_async(
                lambda: list(GameParticipant.objects.filter(game=game)
                             .select_related('player__profile')
                             .values('player__username', 'player__first_name', 'player__last_name',
                                     'player__profile__vk_id'))
            )()

            state = {
                'game_id': game.id,
                'host_username': game.owner.username,  # ✅ Теперь работает, т.к. owner загружен
                'questions': game.question_set.quiz_set_content,
                'current_idx': -1,
                'timer_seconds': 30,
                'is_running': True,
                'started_at': timezone.now().isoformat(),
                'participants': {
                    p['player__username']: {
                        'username': p['player__username'],
                        'first_name': p['player__first_name'],
                        'last_name': p['player__last_name'],
                        'vk_id': p['player__profile__vk_id'],
                        'score': 0, 'correct': 0, 'total': 0,
                        'answered_current': False, 'answer_time': 0
                    } for p in participants_qs
                }
            }

            self.save_state(state)

            # ✅ Обновляем статус в БД (используем update() для атомарности)
            await sync_to_async(
                lambda: QuizGame.objects.filter(id=game.id).update(
                    status='playing',
                    started_at=timezone.now()
                )
            )()

            await self.channel_layer.group_send(
                f'game_{self.game_code}', {'type': 'game_started'}
            )
            return True
        except QuizGame.DoesNotExist:
            return False

    # ✅ ASYNC метод
    async def next_question(self):
        state = self.get_state()
        if not state or not state.get('is_running'):
            return None

        state['current_idx'] += 1
        if state['current_idx'] >= len(state['questions']):
            await self.end_game()
            return None

        for username in state['participants']:
            state['participants'][username]['answered_current'] = False
            state['participants'][username]['answer_time'] = 0

        question = state['questions'][state['current_idx']]
        self.save_state(state)

        return {
            'question_number': state['current_idx'] + 1,
            'total_questions': len(state['questions']),
            'text': question['question'],
            'options': question['options'],
            'timer': state['timer_seconds']
        }

    # ✅ SYNC метод (вызывается из обычного HTTP view)
    def handle_answer(self, username: str, option_index: int) -> dict:
        state = self.get_state()
        if not state: return {'success': False, 'error': 'Game not found'}
        if username not in state['participants']: return {'success': False, 'error': 'Player not in game'}

        player = state['participants'][username]
        if player['answered_current']: return {'success': False, 'error': 'Already answered'}

        question = state['questions'][state['current_idx']]
        is_correct = option_index == question.get('correctIndex', -1)

        player['answered_current'] = True
        player['correct'] = is_correct
        player['answer_time'] = state['timer_seconds']

        if is_correct:
            speed_bonus = max(0, (state['timer_seconds'] - player['answer_time']) * 5)
            player['score'] += 100 + speed_bonus
        player['total'] += 1
        self.save_state(state)

        # Отправка в WS из sync контекста
        async_to_sync(self.channel_layer.group_send)(
            f'game_{self.game_code}',
            {'type': 'player_answer', 'username': username, 'correct': is_correct}
        )
        return {'success': True, 'correct': is_correct}

    async def finish_question(self):
        state = self.get_state()
        if not state: return
        await self._save_results_to_db(state)

        leaderboard = sorted(state['participants'].values(), key=lambda x: x['score'], reverse=True)
        await self.channel_layer.group_send(
            f'game_{self.game_code}',
            {'type': 'leaderboard_update', 'leaderboard': [
                {'name': f"{p['first_name']} {p['last_name']}" if p['first_name'] else p['username'],
                 'score': p['score'], 'correct': p['correct'], 'total': p['total']}
                for p in leaderboard
            ]}
        )
        await self.channel_layer.group_send(f'game_{self.game_code}', {'type': 'question_ended'})

    async def end_game(self):
        state = self.get_state()
        if not state: return
        try:
            await sync_to_async(lambda: QuizGame.objects.filter(game_code=self.game_code).update(
                status='finished', finished_at=timezone.now()
            ))()
            await self._save_results_to_db(state)
            await self.channel_layer.group_send(f'game_{self.game_code}', {'type': 'game_ended'})
            redis_client.delete(self.redis_key)
        except Exception:
            redis_client.delete(self.redis_key)

    async def _save_results_to_db(self, state):
        try:
            game_id = state['game_id']
            for uname, data in state['participants'].items():
                await sync_to_async(lambda u=uname, d=data: GameResult.objects.update_or_create(
                    game_id=game_id, player__username=u,
                    defaults={'score': d['score'], 'correct_answers': d['correct']}
                ))()
        except Exception as e:
            print(f"Error saving results: {e}")

    def get_participants_for_bot(self):
        state = self.get_state()
        if not state: return []

        host_username = state.get('host_username')

        # ✅ ИСКЛЮЧАЕМ ВЕДУЩЕГО ИЗ РАССЫЛКИ
        return [
            {'vk_id': p['vk_id'], 'username': p['username'],
             'name': f"{p['first_name']} {p['last_name']}" if p['first_name'] else p['username']}
            for p in state['participants'].values()
            if p['vk_id'] and p['username'] != host_username
        ]


def get_game_session(game_code: str) -> GameSession:
    return GameSession(game_code)
