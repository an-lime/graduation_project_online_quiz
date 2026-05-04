from django.contrib.auth.models import User
from django.db import models
from django.db.models import JSONField


class QuizQuestionSet(models.Model):
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
        verbose_name = "Набор вопросов"
        verbose_name_plural = "Наборы вопросов"

    def __str__(self):
        return self.name

    def get_questions_count(self):
        """Количество вопросов в наборе"""
        return len(self.quiz_set_content)

    def get_question(self, index):
        """Получить вопрос по индексу"""
        if 0 <= index < len(self.quiz_set_content):
            return self.quiz_set_content[index]
        return None

    def add_question(self, question_data):
        """Добавить новый вопрос"""
        self.quiz_set_content.append(question_data)
        self.save()

    def delete_question(self, index):
        """Удалить вопрос"""
        if 0 <= index < len(self.quiz_set_content):
            self.quiz_set_content.pop(index)
            self.save()

    def shuffle_questions(self):
        """Перемешать вопросы"""
        import random
        random.shuffle(self.quiz_set_content)
        self.save()


class QuizGame(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Ожидание игроков'),
        ('playing', 'Игра идёт'),
        ('finished', 'Игра завершена'),
    ]

    owner = models.ForeignKey(User, verbose_name='Ведущий викторины', on_delete=models.PROTECT, related_name='quiz_games')
    name = models.CharField(verbose_name="Название викторины", max_length=150)

    question_set = models.ForeignKey(QuizQuestionSet, verbose_name='Набор вопросов', on_delete=models.PROTECT,
                                     related_name='games')
    game_code = models.CharField(verbose_name="Код комнаты", unique=True, max_length=8, db_index=True)

    status = models.CharField(verbose_name="Статус игры", choices=STATUS_CHOICES, default='waiting')

    participants = models.ManyToManyField(
        User,
        verbose_name='Участники',
        related_name='played_games',
        blank=True,
        through='game_quiz.GameParticipant')
    is_public = models.BooleanField("Доступность игры", default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Игровая сессия"
        verbose_name_plural = "Игровые сессии"

    def __str__(self):
        return self.name


class GameResult(models.Model):
    game = models.ForeignKey(QuizGame, on_delete=models.CASCADE, related_name='results')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_results')

    score = models.PositiveIntegerField(verbose_name="Очки", default=0)

    rank = models.PositiveIntegerField(verbose_name="Место в игре", null=True, blank=True)

    class Meta:
        unique_together = ('game', 'player')
        verbose_name = "Результат игры"
        verbose_name_plural = "Результаты игр"

class GameParticipant(models.Model):
    """Промежуточная модель: участник конкретной игры"""

    game = models.ForeignKey(QuizGame, on_delete=models.CASCADE)
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'player')
        verbose_name = "Участник игры"
        verbose_name_plural = "Участники игр"

    def __str__(self):
        return f"{self.player.username} в игре {self.game.name}"