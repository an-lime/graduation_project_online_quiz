from django.shortcuts import render

from game_quiz.models import QuizGame


def index(request):
    active_game = None
    if request.user.is_authenticated:
        active_game = QuizGame.objects.filter(
            owner=request.user,
            status__in=['waiting', 'playing']
        ).first()

    return render(request, 'main/index.html', {'active_game': active_game})


def about(request):
    """Страница О проекте"""
    return render(request, 'main/about.html')


def rules(request):
    """Страница Правила игры"""
    return render(request, 'main/rules.html')


def contacts(request):
    """Страница Контакты"""
    return render(request, 'main/contacts.html')
