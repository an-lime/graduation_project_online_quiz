from django.contrib import admin

from .models import QuizQuestionSet, QuizGame, GameResult, GameParticipant


# 1. Встраиваемые блоки (Inlines) - показывают связанные данные прямо внутри игры
class GameParticipantInline(admin.TabularInline):
    model = GameParticipant
    extra = 0
    readonly_fields = ('joined_at',)
    autocomplete_fields = ('player',)


class GameResultInline(admin.TabularInline):
    model = GameResult
    extra = 0
    ordering = ('-score',)
    autocomplete_fields = ('player',)


# 2. Настройка самих моделей
@admin.register(QuizGame)
class QuizGameAdmin(admin.ModelAdmin):
    list_display = ('game_code', 'name', 'owner', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('game_code', 'name', 'owner__username')
    autocomplete_fields = ('owner', 'question_set')

    # Подключаем встраиваемые таблицы
    inlines = [GameParticipantInline, GameResultInline]

    # Группируем поля на странице редактирования по логическим блокам
    fieldsets = (
        ('Основная информация об игре', {
            'fields': ('game_code', 'name', 'status')
        }),
        ('Связи и настройки', {
            'fields': ('owner', 'question_set')
        }),
    )

    # Запрещаем изменять код игры после её создания
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Если объект уже существует
            return ['game_code']
        return []


@admin.register(QuizQuestionSet)
class QuizQuestionSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_public', 'created_at', 'get_questions_count')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'owner__username')
    autocomplete_fields = ('owner',)
    list_editable = ('is_public',)


@admin.register(GameResult)
class GameResultAdmin(admin.ModelAdmin):
    list_display = ('game', 'player', 'score', 'rank')
    list_filter = ('game__name',)
    search_fields = ('player__username', 'game__game_code')
    autocomplete_fields = ('game', 'player')


@admin.register(GameParticipant)
class GameParticipantAdmin(admin.ModelAdmin):
    list_display = ('game', 'player', 'joined_at')
    search_fields = ('player__username', 'game__game_code')
