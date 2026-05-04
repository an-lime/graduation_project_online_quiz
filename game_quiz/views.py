import json
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from game_quiz.models import QuizQuestionSet, QuizGame, GameParticipant


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
    game = get_object_or_404(QuizGame, game_code=code, owner=request.user)

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
            # Генерируем новый уникальный код, если этот занят
            while True:
                new_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
                if not QuizGame.objects.filter(game_code=new_code).exists():
                    game_code = new_code
                    break

        question_set = get_object_or_404(QuizQuestionSet, id=quiz_set_id)

        game = QuizGame.objects.create(
            owner=request.user,
            name=game_name,
            question_set=question_set,
            game_code=game_code,
            is_public=is_public
        )

        GameParticipant.objects.get_or_create(
            game=game,
            player=request.user,
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
