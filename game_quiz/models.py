"""
Модуль моделей приложения викторины (game_quiz).

Содержит модели для управления наборами вопросов, игровыми сессиями,
результатами игр и участниками. Обеспечивает хранение данных для
онлайн-викторин с возможностью создания публичных и приватных игр.
"""

import random

from django.contrib.auth.models import User
from django.db import models
from django.db.models import JSONField


class QuizQuestionSet(models.Model):
    """
    Модель набора вопросов для викторины.

    Представляет собой коллекцию вопросов в формате JSON, которая может
    быть использована в различных игровых сессиях. Наборы могут быть
    публичными (доступны всем) или приватными (только для владельца).

    Attributes:
        owner: Владелец набора вопросов (пользователь Django).
        name: Название набора (максимум 100 символов).
        quiz_set_content: JSON-поле со списком вопросов.
        is_public: Флаг публичности набора.
        created_at: Дата и время создания набора.
        updated_at: Дата и время последнего изменения.
    """
    owner = models.ForeignKey(User, verbose_name='Автор набора', on_delete=models.CASCADE, related_name='quiz_sets')

    name = models.CharField(verbose_name="Название набора", max_length=100)

    quiz_set_content = JSONField(
        verbose_name="Вопросы",
        default=list,
    )

    is_public = models.BooleanField("Публичный набор", default=False)

    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='Последнее изменение', auto_now=True)

    class Meta:
        """Мета-настройки модели."""
        verbose_name = "Набор вопросов"
        verbose_name_plural = "Наборы вопросов"

    def __str__(self):
        """Возвращает название набора вопросов."""
        return self.name

    def get_questions_count(self):
        """
        Получение количества вопросов в наборе.

        Returns:
            int: Количество вопросов в наборе.
        """
        return len(self.quiz_set_content)

    def get_question(self, index):
        """
        Получение вопроса по индексу.

        Args:
            index: Индекс вопроса в списке (начиная с 0).

        Returns:
            dict: Данные вопроса или None, если индекс вне диапазона.
        """
        if 0 <= index < len(self.quiz_set_content):
            return self.quiz_set_content[index]
        return None

    def add_question(self, question_data):
        """
        Добавление нового вопроса в набор.

        Args:
            question_ Словарь с данными вопроса для добавления.
        """
        self.quiz_set_content.append(question_data)
        self.save()

    def delete_question(self, index):
        """
        Удаление вопроса из набора по индексу.

        Args:
            index: Индекс вопроса для удаления.
        """
        if 0 <= index < len(self.quiz_set_content):
            self.quiz_set_content.pop(index)
            self.save()


class QuizGame(models.Model):
    """
    Модель игровой сессии викторины.

    Представляет собой конкретную игру с уникальным кодом для подключения,
    набором вопросов и статусом выполнения. Поддерживает многопользовательский
    режим через модель GameParticipant.

    Attributes:
        owner: Ведущий игры (пользователь Django).
        name: Название викторины (максимум 150 символов).
        question_set: Набор вопросов, используемый в игре.
        game_code: Уникальный 4-значный код для подключения к игре.
        status: Текущий статус игры ('waiting', 'playing', 'finished').
        participants: Участники игры (многие-ко-многим через GameParticipant).
        is_public: Флаг доступности игры для всех пользователей.
        created_at: Дата и время создания игры.
        started_at: Дата и время начала игры.
        finished_at: Дата и время завершения игры.
    """
    STATUS_CHOICES = [
        ('waiting', 'Ожидание игроков'),
        ('playing', 'Игра идёт'),
        ('finished', 'Игра завершена'),
    ]

    owner = models.ForeignKey(User, verbose_name='Ведущий викторины', on_delete=models.PROTECT,
                              related_name='quiz_games')
    name = models.CharField(verbose_name="Название викторины", max_length=150)

    question_set = models.ForeignKey(QuizQuestionSet, verbose_name='Набор вопросов', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='games')
    game_code = models.CharField(verbose_name="Код комнаты", unique=True, max_length=8, db_index=True)

    status = models.CharField(verbose_name="Статус игры", choices=STATUS_CHOICES, default='waiting')

    participants = models.ManyToManyField(
        User,
        verbose_name='Участники',
        related_name='played_games',
        blank=True,
        through='game_quiz.GameParticipant')
    is_public = models.BooleanField("Доступность игры", default=False)

    created_at = models.DateTimeField(verbose_name="Дата создания", auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Мета-настройки модели."""
        verbose_name = "Игровая сессия"
        verbose_name_plural = "Игровые сессии"

    def __str__(self):
        """Возвращает название викторины."""
        return self.name

    @classmethod
    def generate_unique_code(cls):
        """
        Генерация уникального 4-значного кода комнаты.

        Создает случайный код из символов (исключая похожие символы like I, 1, O, 0)
        и проверяет его уникальность в базе данных.

        Returns:
            str: Уникальный 4-символьный код комнаты.
        """
        while True:
            code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
            if not cls.objects.filter(game_code=code).exists():
                return code


class GameResult(models.Model):
    """
    Модель результата игры пользователя.

    Хранит информацию о результате конкретного игрока в определенной игре:
    набранные очки и занятое место.

    Attributes:
        game: Ссылка на игру, в которой был получен результат.
        player: Игрок, получивший результат.
        score: Количество набранных очков.
        rank: Занятое место в игре (1 - первое место и т.д.).
    """
    game = models.ForeignKey(QuizGame, on_delete=models.CASCADE, related_name='results', verbose_name='Викторина')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_results', verbose_name='Участник')

    score = models.PositiveIntegerField(verbose_name="Очки", default=0)

    rank = models.PositiveIntegerField(verbose_name="Место в игре", null=True, blank=True)

    class Meta:
        """Мета-настройки модели."""
        unique_together = ('game', 'player')
        verbose_name = "Результат игры"
        verbose_name_plural = "Результаты игр"


class GameParticipant(models.Model):
    """
    Промежуточная модель участника конкретной игры.

    Служит для реализации связи многие-ко-многим между пользователями
    и играми. Позволяет отслеживать время присоединения участника к игре.

    Attributes:
        game: Игра, в которой участвует пользователь.
        player: Участник игры (может быть null для ботов/гостей).
        joined_at: Дата и время присоединения к игре.
    """

    game = models.ForeignKey(QuizGame, on_delete=models.CASCADE, verbose_name='Викторина')
    player = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Участник')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Время присоединения')

    class Meta:
        """Мета-настройки модели."""
        unique_together = ('game', 'player')
        verbose_name = "Участник игры"
        verbose_name_plural = "Участники игр"

    def __str__(self):
        """Возвращает строковое представление участника в игре."""
        return f"{self.player.username} в игре {self.game.name}"
