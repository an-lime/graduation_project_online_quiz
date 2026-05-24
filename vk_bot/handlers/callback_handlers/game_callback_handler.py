import asyncio
import logging

import aiohttp
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from environs import Env
from vkbottle import Keyboard, Callback
from vkbottle.bot import Message
from vkbottle_types import GroupTypes

from Online_Quiz_Core.settings import BASE_DIR
from game_quiz.models import QuizGame, GameParticipant
from game_quiz.services.game_session import get_game_session
from vk_bot.keyboards.lobby_keyboard import create_lobby_keyboard, create_leave_confirm_keyboard
from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.utils.db import get_current_user
from vk_bot.utils.states import set_state, UserState, clear_state
from vk_bot.utils.support_functions import generate_event_random_id

logger = logging.getLogger(__name__)

env = Env()
env.read_env(BASE_DIR / ".env")
DJANGO_API_URL = env.str("DJANGO_API_URL")


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

    await set_state(event.object.user_id, UserState.WAITING_FOR_CODE)

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

    await clear_state(event.object.user_id)

    kb = create_main_menu_keyboard()
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="❌ Присоединение отменено.",
        keyboard=kb
    )


async def process_game_code(message: Message):
    """Обработка введённого кода комнаты (без FSM, через менеджер состояний)"""

    # 1. Сразу убираем из списка ожидающих, чтобы не зациклить
    await clear_state(message.from_id)

    code = message.text.strip().upper() if message.text else ""
    user = await get_current_user(message.from_id)

    if not user:
        await message.answer("❌ Ошибка авторизации. Напишите /start")
        return

    # 2. Валидация длины кода
    if len(code) != 4:
        await message.answer("❌ Код должен состоять из 4 символов. Попробуйте ещё раз:")
        await set_state(message.from_id, UserState.WAITING_FOR_CODE)  # Возвращаем в режим ожидания
        return

    # 3. Поиск игры
    try:
        game = await sync_to_async(
            lambda: QuizGame.objects.select_related('question_set', 'owner').get(game_code=code)
        )()
    except QuizGame.DoesNotExist:
        await message.answer("❌ Игра с таким кодом не найдена. Проверьте и попробуйте снова:")
        await set_state(message.from_id, UserState.WAITING_FOR_CODE)
        return

    # 4. Проверка статуса игры
    if game.status != 'waiting':
        await message.answer(f"❌ Игра уже идёт, либо завершилась.")
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

    display_name = f"{user.first_name} {user.last_name}".strip()
    if not display_name:
        display_name = user.username

    await channel_layer.group_send(
        f'lobby_{game.game_code}',
        {
            'type': 'participant_joined',
            'username': display_name,
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
        "Ожидайте начала игры. Нажмите 'Покинуть лобби', если передумали.",
        keyboard=kb
    )


async def leave_lobby(event: GroupTypes.MessageEvent, payload: dict):
    """1. Запрос на подтверждение выхода (вызывается из нижней клавиатуры)"""
    game_code = payload.get("game_code", "").upper()
    kb = create_leave_confirm_keyboard(game_code)

    # Так как cmid нет, мы не редактируем, а отправляем НОВОЕ сообщение с инлайн-кнопками
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="❓ Вы уверены, что хотите покинуть игру?",
        keyboard=kb
    )


async def cancel_leave_lobby(event: GroupTypes.MessageEvent, payload: dict):
    """2. Отмена выхода (возврат к клавиатуре лобби)"""
    game_code = payload.get("game_code", "").upper()
    kb = create_lobby_keyboard(game_code)
    message_text = "Вы остались в лобби. Ожидайте начала игры."

    # Безопасно проверяем наличие cmid у инлайн-кнопки отмены
    cmid = getattr(event.object, 'conversation_message_id', None)

    if cmid and cmid != 0:
        try:
            await event.ctx_api.messages.edit(
                peer_id=event.object.peer_id,
                conversation_message_id=cmid,
                message=message_text,
                keyboard=kb
            )
            return
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение при отмене выхода: {e}")

    # Если cmid не нашелся, просто отправляем новое сообщение
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message=message_text,
        keyboard=kb
    )


async def confirm_leave_lobby(event: GroupTypes.MessageEvent, payload: dict):
    """3. Подтверждённый выход из лобби или активной игры (с защитой от повторных кликов)"""
    game_code = payload.get("game_code", "").upper()
    user_id = event.object.user_id
    user = await get_current_user(user_id)

    if not user or not game_code:
        return

    was_removed = False
    game_aborted = False

    first_name = user.first_name.strip() if user.first_name else ""
    last_name = user.last_name.strip() if user.last_name else ""
    full_name = f"{first_name} {last_name}".strip()
    display_name = full_name if full_name else user.username

    try:
        # 1. Проверяем и удаляем участника из БД Django
        participant = await sync_to_async(
            lambda: GameParticipant.objects.select_related('player', 'game__owner').get(
                game__game_code=game_code,
                player=user
            )
        )()
        game = participant.game

        # Удаляем игрока
        await sync_to_async(participant.delete)()
        was_removed = True

        # ПРОБЛЕМА РЕШЕНА: Проверяем, остались ли еще обычные игроки (кроме создателя) в БД
        remaining_players = await sync_to_async(
            lambda: GameParticipant.objects.filter(game=game).exists()
        )()

        if not remaining_players:
            # Если это был последний игрок, экстренно удаляем игру из БД до старта!
            await sync_to_async(game.delete)()
            game_aborted = True

    except GameParticipant.DoesNotExist:
        pass

    # 2. Пробуем удалить из Redis-сессии (если игра уже была запущена)
    session = get_game_session(game_code)
    channel_layer = get_channel_layer()

    if game_aborted:
        # Если игра отменена на этапе БД, рассылаем сигнал смерти игры и чистим Redis
        await session._abort_game()
        # Дублируем сигнал в лобби на всякий случай
        await channel_layer.group_send(f'lobby_{game_code}', {'type': 'game_aborted'})
    else:
        # Обычное удаление из Redis (внутри себя тоже может отменить игру, если она шла)
        redis_removed = await session.remove_player(user_id)
        if redis_removed:
            was_removed = True

        # 3. Рассылаем обычные сигналы выхода в браузер
        if was_removed:
            await channel_layer.group_send(
                f'lobby_{game_code}',
                {'type': 'participant_left', 'username': display_name, 'vk_id': user_id}
            )
            await channel_layer.group_send(
                f'game_{game_code}',
                {'type': 'participant_left', 'username': display_name, 'vk_id': user_id}
            )

    # 4. Отправляем меню пользователю
    if was_removed:
        message_text = "✅ Вы успешно покинули игру."
    else:
        message_text = "ℹ️ Вы уже покинули эту игру или лобби больше не существует."

    kb = create_main_menu_keyboard()
    cmid = getattr(event.object, 'conversation_message_id', None)

    if cmid and cmid != 0:
        try:
            await event.ctx_api.messages.edit(
                peer_id=event.object.peer_id,
                conversation_message_id=cmid,
                message=message_text,
                keyboard=kb
            )
            return
        except Exception as e:
            logger.warning(f"Ошибка редактирования сообщения при подтверждении выхода: {e}")

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message=message_text,
        keyboard=kb
    )


async def handle_answer_callback(event: GroupTypes.MessageEvent, payload: dict):
    """Обработка нажатия на вариант ответа в игре"""
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
                random_id=generate_event_random_id(),
                message="❌ Ошибка: вы не авторизованы в системе викторины."
            )
            return

        # Отправляем ответ на Django с использованием aiohttp
        async with aiohttp.ClientSession() as session:
            # aiohttp.ClientTimeout позволяет удобно настроить таймаут
            timeout = aiohttp.ClientTimeout(total=5)

            async with session.post(
                    f"{DJANGO_API_URL}/quiz/api/answer/",
                    json={
                        "game_code": game_code,
                        "vk_id": user_id,
                        "option_index": option_index
                    },
                    timeout=timeout
            ) as resp:
                # Генерируем исключение, если сервер ответил ошибкой (например, 500 или 404)
                resp.raise_for_status()
                # Асинхронно читаем JSON-ответ
                result = await resp.json()

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
                message=f"⏱ Время вышло!"  # <-- исправлены кавычки
            )

    except aiohttp.ClientError as e:
        # aiohttp.ClientError — это базовый класс для всех сетевых ошибок aiohttp
        logger.error(f"🌐 Network error sending answer to Django: {e}")
        await event.ctx_api.messages.edit(
            peer_id=event.object.peer_id,
            cmid=cmid,
            message="⚠️ Ошибка связи с сервером. Попробуйте позже."
        )
    except asyncio.TimeoutError:
        # Отдельно ловим таймаут, если сервер Django "завис"
        logger.error("🌐 Timeout error: Django server took too long to respond.")
        await event.ctx_api.messages.edit(
            peer_id=event.object.peer_id,
            cmid=cmid,
            message="⚠️ Сервер слишком долго не отвечает. Попробуйте позже."
        )
    except Exception as e:
        logger.error(f"💥 Error in handle_answer_callback: {e}", exc_info=True)
