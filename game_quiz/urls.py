from django.urls import path

from game_quiz import views

app_name = 'game_quiz'

urlpatterns = [
    path('', views.create_game, name='create_game'),
    path('list/', views.games_list, name='games_list'),

    # Редактор наборов вопросов
    path('sets/new/', views.set_editor, name='create_set'),
    path('sets/new/save/', views.save_question_set, name='save_new_set'),
    path('sets/edit/<int:set_id>/', views.set_editor, name='edit_set'),
    path('sets/edit/<int:set_id>/save/', views.save_question_set, name='save_set'),

    path('lobby/<str:code>/', views.lobby, name='lobby'),
    path('create-game-ajax/', views.create_game_ajax, name='create_game_ajax'),

    path('set/<int:set_id>/delete/', views.delete_quiz_set_ajax, name='delete_quiz_set_ajax'),

    path('lobby/<str:code>/start/', views.start_lobby_game, name='start_lobby_game'),
    path('lobby/<str:code>/delete/', views.delete_game_ajax, name='delete_game_ajax'),

    path('play/<str:game_code>/', views.game_view, name='game_view'),

    # API для бота
    path('api/answer/', views.api_answer, name='api_answer'),
]
