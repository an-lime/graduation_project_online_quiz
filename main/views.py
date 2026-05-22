from django.shortcuts import render

from game_quiz.models import QuizGame


def index(request):
    """
    Главная страница проекта.

    Отображает основную страницу с информацией о проекте.
    Для авторизованных пользователей показывает активную игру (если есть),
    чтобы обеспечить быстрый доступ к панели управления игрой.

    Args:
        request: HTTP запрос от пользователя.

    Returns:
        HttpResponse: Рендеринг шаблона main/index.html с контекстом активной игры.
    """
    active_game = None
    if request.user.is_authenticated:
        active_game = QuizGame.objects.filter(
            owner=request.user,
            status__in=['waiting', 'playing']
        ).first()

    return render(request, 'main/index.html', {'active_game': active_game})


def about(request):
    """
    Страница 'О проекте'.

    Предоставляет информацию о проекте онлайн-викторины,
    его целях и возможностях.

    Args:
        request: HTTP запрос от пользователя.

    Returns:
        HttpResponse: Рендеринг шаблона main/about.html.
    """
    return render(request, 'main/about.html')


def rules(request):
    """
    Страница 'Правила игры'.

    Содержит описание правил проведения викторин,
    систему начисления очков и условия победы.

    Args:
        request: HTTP запрос от пользователя.

    Returns:
        HttpResponse: Рендеринг шаблона main/rules.html.
    """
    return render(request, 'main/rules.html')


def contacts(request):
    """
    Страница 'Контакты'.

    Предоставляет контактную информацию для связи
    с разработчиками или службой поддержки.

    Args:
        request: HTTP запрос от пользователя.

    Returns:
        HttpResponse: Рендеринг шаблона main/contacts.html.
    """
    return render(request, 'main/contacts.html')
