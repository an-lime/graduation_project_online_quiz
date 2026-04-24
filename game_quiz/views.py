import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from game_quiz.models import QuizQuestionSet


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

    initial_questions = []
    if question_set:
        initial_questions = question_set.quiz_set_content

    return render(request, 'game_quiz/set_editor.html', {
        'question_set': question_set,
        'title': title,
        'initial_questions': initial_questions,
        'set_name': question_set.name if question_set else ''
    })


@login_required
@require_POST
def save_question_set(request, set_id=None):
    """Сохранение набора вопросов (AJAX)"""

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        questions = data.get('questions', [])

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
        else:
            question_set = QuizQuestionSet.objects.create(
                owner=request.user,
                name=name,
                quiz_set_content=questions
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
