import json
from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from game_quiz.models import QuizGame, GameParticipant
from game_quiz.models import QuizQuestionSet
from game_quiz.services.game_session import get_game_session, redis_client

User = get_user_model()


@login_required
def create_game(request):
    my_sets = QuizQuestionSet.objects.filter(owner=request.user).order_by('-updated_at')
    public_sets = QuizQuestionSet.objects.filter(
        is_public=True,
    ).exclude(owner=request.user).order_by('-updated_at')

    return render(request, 'game_quiz/create_game.html', {
        'my_sets': my_sets,
        'public_sets': public_sets,
    })


@login_required
def games_list(request):
    """Список публичных активных игр"""
    public_games = QuizGame.objects.filter(
        is_public=True,
        status__in=['waiting', 'playing']
    ).select_related('owner', 'question_set').order_by('-created_at')

    return render(request, 'game_quiz/games_list.html', {
        'public_games': public_games,
    })


@login_required
def set_editor(request, set_id=None):
    if set_id:
        question_set = get_object_or_404(QuizQuestionSet, id=set_id, owner=request.user)
        title = "Редактирование набора"
    else:
        question_set = None
        title = "Создание нового набора"

    initial_questions_json = '[]'
    if question_set and question_set.quiz_set_content:
        initial_questions_json = json.dumps(question_set.quiz_set_content)

    return render(request, 'game_quiz/set_editor.html', {
        'question_set': question_set,
        'title': title,
        'initial_questions_json': initial_questions_json,
        'set_name': question_set.name if question_set else '',
        'is_public': question_set.is_public if question_set else False,
    })


@login_required
@require_POST
def save_question_set(request, set_id=None):
    """Сохранение набора вопросов (AJAX)"""

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        questions = data.get('questions', [])
        is_public = data.get('is_public', False)

        if not name:
            return JsonResponse({'success': False, 'error': 'Введите название набора'})

        if not questions or len(questions) == 0:
            return JsonResponse({'success': False, 'error': 'Добавьте хотя бы один вопрос'})

        for idx, q in enumerate(questions):
            if not q.get('question'):
                return JsonResponse({'success': False, 'error': f'Вопрос #{idx + 1} пустой'})
            if not q.get('options') or len(q['options']) < 2:
                return JsonResponse({'success': False, 'error': f'Вопрос #{idx + 1}: минимум 2 варианта'})
            if q.get('correctIndex', -1) == -1:
                return JsonResponse({'success': False, 'error': f'Вопрос #{idx + 1}: не указан правильный ответ'})

        if set_id:
            question_set = QuizQuestionSet.objects.get(id=set_id, owner=request.user)
            question_set.name = name
            question_set.quiz_set_content = questions
            question_set.is_public = is_public
            question_set.save()
        else:
            question_set = QuizQuestionSet.objects.create(
                owner=request.user,
                name=name,
                quiz_set_content=questions,
                is_public=is_public
            )

        return JsonResponse({
            'success': True,
            'message': 'Набор успешно сохранён!',
            'set_id': question_set.id
        })

    except QuizQuestionSet.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Набор не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})


@login_required
def lobby(request, code):
    # Пытаемся найти игру по коду
    try:
        game = QuizGame.objects.get(game_code=code)
    except QuizGame.DoesNotExist:
        # Если код неверный, показываем ошибку и возвращаем к списку
        return redirect('game_quiz:games_list')  # Убедись, что 'game_quiz:games_list' совпадает с твоим urls.py

    # Запрещаем заходить в лобби, если игра уже началась или завершена
    if game.status != 'waiting':
        return redirect('game_quiz:games_list')

    participants = game.participants.all()

    return render(request, 'game_quiz/lobby.html', {
        'game': game,
        'game_code': code,
        'quiz_name': game.name,
        'participants': participants,
        'player_count': participants.count()
    })


@login_required
@require_POST
@transaction.atomic
def create_game_ajax(request):
    try:

        active_game = QuizGame.objects.filter(
            owner=request.user,
            status__in=['waiting', 'playing']
        ).first()

        if active_game:
            return JsonResponse({
                'success': False,
                'error': f'У вас уже есть активная игра (код {active_game.game_code}). Сначала завершите её!'
            })

        data = json.loads(request.body)

        quiz_set_id = data.get('quiz_set_id')
        game_name = data.get('game_name', '').strip()
        game_code = data.get('game_code', '').strip().upper()
        is_public = data.get('is_public', False)

        if not quiz_set_id:
            return JsonResponse({'success': False, 'error': 'Выберите набор вопросов'})

        if len(game_name) < 3:
            return JsonResponse({'success': False, 'error': 'Название игры должно содержать минимум 3 символа'})

        if len(game_code) != 4:
            return JsonResponse({'success': False, 'error': 'Некорректный код комнаты'})

        if QuizGame.objects.filter(game_code=game_code).exists():
            game_code = QuizGame.generate_unique_code()

        question_set = get_object_or_404(QuizQuestionSet, id=quiz_set_id)

        game = QuizGame.objects.create(
            owner=request.user,
            name=game_name,
            question_set=question_set,
            game_code=game_code,
            is_public=is_public
        )

        return JsonResponse({
            'success': True,
            'message': 'Игра создана!',
            'game_code': game_code,
            'game_id': game.id
        })

    except QuizQuestionSet.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Набор вопросов не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})


@login_required
@require_POST
def start_lobby_game(request, code):
    """Запуск игры из лобби (AJAX)"""
    try:
        game = get_object_or_404(QuizGame, game_code=code, owner=request.user)

        if game.status != 'waiting':
            return JsonResponse({'success': False, 'error': 'Игра уже запущена или завершена'})

        # Инициализация сессии и запуск
        session = get_game_session(code)
        success = session.start_game()

        if success:

            return JsonResponse({
                'success': True,
                'message': 'Игра запущена!',
                'redirect_url': f'/quiz/play/{code}/'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Ошибка инициализации сессии'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def game_view(request, game_code):
    game_code = game_code.upper()
    game = get_object_or_404(QuizGame, game_code=game_code)

    if game.status == 'waiting':
        if request.user == game.owner:
            game.status = 'playing'
            if not game.started_at:
                game.started_at = timezone.now()
            game.save()
        else:
            return redirect('game_quiz:lobby', code=game_code)

    # Загружаем участников, исключая ведущего (он выводится отдельно)
    participants = GameParticipant.objects.filter(game=game).exclude(player=game.owner).select_related(
        'player__profile')

    return render(request, 'game_quiz/game_view.html', {
        'game': game,
        'game_code': game_code,
        'is_host': request.user == game.owner,
        'participants': participants,  # ✅ Передаём в контекст
    })


@csrf_exempt
def api_answer(request):
    """
    API endpoint для получения ответов от бота
    POST /quiz/api/answer/
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    data = json.loads(request.body)
    game_code = data.get('game_code', '').upper()
    vk_id = data.get('vk_id')
    option_index = data.get('option_index')

    try:
        game = QuizGame.objects.get(game_code=game_code)
    except QuizGame.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Игра уже завершена или была отменена."
        })

    if not all([game_code, vk_id, option_index is not None]):
        return JsonResponse({'error': 'Missing fields'}, status=400)

    try:
        redis_key = f"game_session:{game_code}"
        state = json.loads(redis_client.get(redis_key))

        started_at = datetime.fromisoformat(state['started_at'])
        current_time = timezone.now()
        time_diff = current_time - started_at

        state['answer_time'] = int(time_diff.total_seconds())
        print(state['answer_time'])
        redis_client.setex(redis_key, getattr(settings, 'REDIS_TTL', None), json.dumps(state))

        session = get_game_session(game_code)
        result = session.handle_answer(vk_id, option_index)

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def delete_game_ajax(request, code):
    """Удаление (отмена) игры ведущим прямо из лобби"""
    try:
        # Проверяем безопасность: удалить комнату может только её создатель
        game = get_object_or_404(QuizGame, game_code=code, owner=request.user)

        # Очищаем данные активной сессии из оперативной памяти Redis
        redis_key = f"game_session:{code}"
        redis_client.delete(redis_key)

        # Рассылаем сигнал отмены всем подключенным к лобби игрокам через веб-сокеты

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'lobby_{code}',
            {
                'type': 'game_aborted'
            }
        )

        # Удаляем игру из базы данных (участники и связи очистятся каскадно)
        game.delete()

        return JsonResponse({'success': True, 'message': 'Игра успешно отменена и удалена!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
