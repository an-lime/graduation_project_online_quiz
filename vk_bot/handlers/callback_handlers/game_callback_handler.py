import asyncio
import logging

import requests
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from environs import Env
from vkbottle import Keyboard, Callback
from vkbottle.bot import Message
from vkbottle_types import GroupTypes

from Online_Quiz_Core.settings import BASE_DIR
from game_quiz.models import QuizGame, GameParticipant
from vk_bot.keyboards.lobby_keyboard import create_lobby_keyboard
from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.services.game_service import GameAnswerHandler
from vk_bot.utils.db import get_current_user
from vk_bot.utils.states import mark_waiting, clear_waiting
from vk_bot.utils.support_functions import generate_event_random_id

logger = logging.getLogger(__name__)

answer_handler = GameAnswerHandler()

env = Env()
env.read_env(BASE_DIR / ".env")


async def join_game(event: GroupTypes.MessageEvent):
    """Начало процесса: переводим в режим ожидания кода"""

    user = await get_current_user(event.object.user_id)
    if not user:
        kb = (
            Keyboard()
            .add(Callback("Создать профиль", {"action": "create_profile"}))
            .row()
            .add(Callback("Назад", {"action": "go_main"}))
        ).get_json()
        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            random_id=generate_event_random_id(),
            message="У вас нет аккаунта! Сначала создайте профиль.",
            keyboard=kb
        )
        return

    mark_waiting(event.object.user_id)

    kb = (
        Keyboard()
        .add(Callback("Отмена", {"action": "cancel_join"}))
    ).get_json()

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="🎮 Введите код комнаты (4 символа):",
        keyboard=kb
    )


async def cancel_join(event: GroupTypes.MessageEvent):
    """Отмена ввода кода"""

    clear_waiting(event.object.user_id)

    kb = create_main_menu_keyboard()
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="❌ Присоединение отменено.",
        keyboard=kb
    )


async def proccess_game_code(message: Message):
    """Обработка введённого кода комнаты (без FSM, через менеджер состояний)"""

    # 1. Сразу убираем из списка ожидающих, чтобы не зациклить
    clear_waiting(message.from_id)

    code = message.text.strip().upper() if message.text else ""
    user = await get_current_user(message.from_id)

    if not user:
        await message.answer("❌ Ошибка авторизации. Напишите /start")
        return

    # 2. Валидация длины кода
    if len(code) != 4:
        await message.answer("❌ Код должен состоять из 4 символов. Попробуйте ещё раз:")
        mark_waiting(message.from_id)  # Возвращаем в режим ожидания
        return

    # 3. Поиск игры
    # ✅ ВАЖНОЕ ИСПРАВЛЕНИЕ: select_related загружает question_set и owner сразу.
    # Это предотвращает ошибку с выводом объекта SyncToAsync и ускоряет работу.
    try:
        game = await sync_to_async(
            lambda: QuizGame.objects.select_related('question_set', 'owner').get(game_code=code)
        )()
    except QuizGame.DoesNotExist:
        await message.answer("❌ Игра с таким кодом не найдена. Проверьте и попробуйте снова:")
        mark_waiting(message.from_id)
        return

    # 4. Проверка статуса игры
    if game.status != 'waiting':
        await message.answer(f"❌ Игра уже {game.get_status_display()}.")
        return

    # 5. Проверка, не присоединён ли пользователь уже
    exists = await sync_to_async(
        lambda: GameParticipant.objects.filter(game=game, player=user).exists()
    )()

    if exists:
        await message.answer("✅ Вы уже присоединились к этой игре! Ожидайте начала.")
        return

    # 6. Проверка: не является ли пользователь ведущим
    if game.owner == user:
        await message.answer("⚠️ Вы являетесь ведущим этой игры! Вы автоматически участвуете в ней.")
        return

    # 7. Успешное добавление участника
    await sync_to_async(GameParticipant.objects.create)(game=game, player=user)

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'lobby_{game.game_code}',
        {
            'type': 'participant_joined',
            'username': user.username,
            'is_host': False
        }
    )

    # 8. Получаем актуальное количество участников
    participants_count = await sync_to_async(
        lambda: GameParticipant.objects.filter(game=game).count()
    )()

    kb = create_lobby_keyboard(game.game_code)

    # 9. Отправляем сообщение об успехе
    await message.answer(
        f"✅ Вы успешно присоединились к игре!\n\n"
        f"🎮 Название: {game.name}\n"
        f"👤 Ведущий: {game.owner.first_name} {game.owner.last_name}\n"
        f"👥 Участников: {participants_count}\n"
        f"🧩 Набор: {game.question_set.name}\n\n"
        "Ожидайте начала игры. Нажмите 'Покинуть лобби', если передумали.",
        keyboard=kb
    )


async def leave_lobby(event: GroupTypes.MessageEvent):
    """Обработка выхода участника из лобби"""
    game_code = event.object.payload.get("game_code", "").upper()
    user = await get_current_user(event.object.user_id)

    if not user or not game_code:
        return

    try:
        # 1. Находим запись участника, чтобы взять имя и удалить
        participant = await sync_to_async(
            lambda: GameParticipant.objects.select_related('player').get(
                game__game_code=game_code,
                player=user
            )
        )()

        username = participant.player.username

        # 2. Удаляем участника из БД
        await sync_to_async(participant.delete)()

        # 3. Отправляем событие в WebSocket (ручная отправка, как в join)
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'lobby_{game_code}',
            {
                'type': 'participant_left',
                'username': username
            }
        )

        # 4. Отправляем ответ пользователю с кнопкой "Назад"
        kb = create_main_menu_keyboard()

        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            random_id=generate_event_random_id(),
            message="✅ Вы успешно покинули лобби.",
            keyboard=kb
        )

    except GameParticipant.DoesNotExist:
        # Если пользователь и так не в игре (например, двойной клик)
        pass


async def handle_answer_callback(event: GroupTypes.MessageEvent, payload: dict):
    """Обработка нажатия на вариант ответа в игре"""

    DJANGO_API_URL = env.str("DJANGO_API_URL")
    try:
        game_code = payload.get("game_code", "").upper()
        option_index = payload.get("option_index")
        user_id = event.object.user_id
        peer_id = event.object.peer_id
        cmid = event.object.conversation_message_id

        if option_index is None or not game_code:
            logger.warning(f"❌ Invalid payload: {payload}")
            return

        # Получаем пользователя из БД
        user = await get_current_user(user_id)
        if not user:
            await event.ctx_api.messages.send(
                peer_id=peer_id,
                random_id=0,
                message="❌ Ошибка: вы не авторизованы в системе викторины."
            )
            return

        # Отправляем ответ на Django (в отдельном потоке, чтобы не блокировать event loop)
        def send_answer_sync():
            return requests.post(
                f"{DJANGO_API_URL}/quiz/api/answer/",
                json={
                    "game_code": game_code,
                    "username": user.username,
                    "option_index": option_index
                },
                timeout=5
            ).json()

        # ✅ Безопасный вызов синхронного requests в async контексте
        result = await asyncio.to_thread(send_answer_sync)

        # Реакция бота на результат
        if result.get("success"):
            await event.ctx_api.messages.edit(
                peer_id=peer_id,
                cmid=cmid,
                message="✅ Ваш ответ принят!"
            )
        else:
            await event.ctx_api.messages.edit(
                peer_id=peer_id,
                cmid=cmid,
                message=f"⏱ Время вышло или ошибка: {result.get('error', 'попробуйте позже')}"
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error sending answer to Django: {e}")
        await event.ctx_api.messages.edit(
            peer_id=event.object.peer_id,
            cmid=event.object.conversation_message_id,
            message="⚠️ Ошибка связи с сервером. Попробуйте позже."
        )
    except Exception as e:
        logger.error(f"💥 Error in handle_answer_callback: {e}", exc_info=True)