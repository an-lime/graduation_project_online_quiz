from django.contrib.auth.models import User
from django.test import TestCase

from game_quiz.models import QuizQuestionSet


class QuizQuestionSetTests(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.question_set = QuizQuestionSet.objects.create(
            owner=self.user,
            name='Test Quiz Set',
            quiz_set_content=[
                {
                    'question': 'What is 2+2?',
                    'options': ['3', '4', '5', '6'],
                    'correctIndex': 1
                },
                {
                    'question': 'What is the capital of France?',
                    'options': ['London', 'Berlin', 'Paris', 'Madrid'],
                    'correctIndex': 2
                }
            ]
        )

    def test_get_questions_count(self):
        """Тест подсчета количества вопросов в наборе"""
        count = self.question_set.get_questions_count()
        self.assertEqual(count, 2)

    def test_get_question_valid_index(self):
        """Тест получения вопроса по валидному индексу"""
        question = self.question_set.get_question(0)
        self.assertIsNotNone(question)
        self.assertEqual(question['question'], 'What is 2+2?')
        self.assertEqual(question['correctIndex'], 1)

    def test_get_question_invalid_index(self):
        """Тест получения вопроса по невалидному индексу"""
        # Индекс за пределами диапазона
        question = self.question_set.get_question(10)
        self.assertIsNone(question)

        # Отрицательный индекс
        question = self.question_set.get_question(-1)
        self.assertIsNone(question)

    def test_add_question(self):
        """Тест добавления нового вопроса в набор"""
        initial_count = self.question_set.get_questions_count()

        new_question = {
            'question': 'What is the color of the sky?',
            'options': ['Blue', 'Green', 'Red', 'Yellow'],
            'correctIndex': 0
        }

        self.question_set.add_question(new_question)

        new_count = self.question_set.get_questions_count()
        self.assertEqual(new_count, initial_count + 1)

        # Проверяем, что вопрос был добавлен корректно
        last_question = self.question_set.get_question(new_count - 1)
        self.assertEqual(last_question['question'], 'What is the color of the sky?')

    def test_delete_question(self):
        """Тест удаления вопроса из набора"""
        initial_count = self.question_set.get_questions_count()

        # Удаляем первый вопрос
        self.question_set.delete_question(0)

        new_count = self.question_set.get_questions_count()
        self.assertEqual(new_count, initial_count - 1)

        # Проверяем, что остался второй вопрос
        remaining_question = self.question_set.get_question(0)
        self.assertEqual(remaining_question['question'], 'What is the capital of France?')

        # Попытка удалить вопрос по невалидному индексу не должна вызывать ошибку
        self.question_set.delete_question(10)
        # Количество вопросов должно остаться прежним
        self.assertEqual(self.question_set.get_questions_count(), 1)
