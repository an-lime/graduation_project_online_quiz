from django.contrib.auth.models import User
from django.db import models
from django.db.models import JSONField


class QuizQuestionSet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sets')

    name = models.CharField(verbose_name="Название набора", max_length=100)

    quiz_set_content = JSONField(
        verbose_name="Вопросы",
        default=list,
    )

    is_public = models.BooleanField("Публичный набор", default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
