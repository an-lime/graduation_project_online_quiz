from django.urls import path

from game_quiz import views

app_name = 'game_quiz'

urlpatterns = [
    path('', views.create_game, name='create_game'),

    # Редактор наборов вопросов
    path('sets/new/', views.set_editor, name='create_set'),
    path('sets/new/save/', views.save_question_set, name='save_new_set'),
    path('sets/edit/<int:set_id>/', views.set_editor, name='edit_set'),
    path('sets/edit/<int:set_id>/save/', views.save_question_set, name='save_set'),
]
