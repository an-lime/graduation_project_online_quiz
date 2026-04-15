import random
import string
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.utils import timezone
from vkbottle import Callback
from vkbottle import GroupTypes
from vkbottle.tools import Keyboard

from users.utils import terminate_all_user_sessions
from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.utils.db import create_user_and_profile
from vk_bot.utils.db import get_current_user
from vk_bot.utils.support_functions import generate_event_random_id


async def go_main(event: GroupTypes.MessageEvent):
    kb = create_main_menu_keyboard()

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )


async def my_profile(event: GroupTypes.MessageEvent):
    user = await get_current_user(event.object.user_id)
    if user is None:
        kb = (
            Keyboard()
            .add(Callback("Создать профиль", {"action": "create_profile"}))
            .row()
            .add(Callback("Назад", {"action": "go_main"}))
        ).get_json()

        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            random_id=generate_event_random_id(),
            message="У вас нет аккаунта!",
            keyboard=kb
        )
    else:

        kb = (
            Keyboard()
            .add(Callback("Сбросить пароль", {"action": "reset_password"}))
            .row()
            .add(Callback("Назад", {"action": "go_main"}))
        ).get_json()

        if event.object.conversation_message_id:
            await event.ctx_api.messages.edit(
                peer_id=event.object.peer_id,
                cmid=event.object.conversation_message_id,
                message=
                "Ваш профиль:\n\n"
                f"Логин: {user.username}\n",
                keyboard=kb
            )
        else:
            await event.ctx_api.messages.send(
                peer_id=event.object.peer_id,
                random_id=generate_event_random_id(),
                message=
                "Ваш профиль:\n\n"
                f"Логин: {user.username}\n",
                keyboard=kb
            )


async def create_profile(event: GroupTypes.MessageEvent):
    username = f"vk_{event.object.user_id}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    await create_user_and_profile(username, password, event)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message=
        f"Ваш аккаунт успешно создан!\n\n"
        f"Логин: {username}\n"
        f"Пароль: {password}\n\n"
        f"Запишите пароль и нажмите кнопку \"Скрыть\", чтобы скрыть его из сообщения\n"
        f"Придумать собственный пароль вы можете на сайте викторины, указанном в описании сообщества",
        keyboard=Keyboard(inline=True).add(Callback("Скрыть", {"action": "hide_password"})).get_json()
    )

    kb = create_main_menu_keyboard()

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )


async def hide_password(event: GroupTypes.MessageEvent):
    await event.ctx_api.messages.edit(
        peer_id=event.object.peer_id,
        cmid=event.object.conversation_message_id,
        message="Пароль аккаунта скрыт",
    )


async def reset_password(event: GroupTypes.MessageEvent):
    kb = (Keyboard(inline=True)
          .add(Callback("✅ Да, сменить", {"action": "confirm_reset"}))
          .row()
          .add(Callback("❌ Отмена", {"action": "my_profile"}))
          ).get_json()

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=generate_event_random_id(),
        message="Вы уверены, что хотите сбросить пароль?",
        keyboard=kb
    )


async def confirm_reset(event: GroupTypes.MessageEvent):
    user = await get_current_user(event.object.user_id)
    if user.profile.last_password_reset:
        if timezone.now() - user.profile.last_password_reset < timedelta(minutes=5):
            await event.ctx_api.messages.send(
                peer_id=event.object.peer_id,
                random_id=generate_event_random_id(),
                message="Подождите 5 минут перед следующим сбросом пароля."
            )
            return

    password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    await sync_to_async(lambda: user.set_password(password))()
    user.profile.last_password_reset = timezone.now()
    await sync_to_async(lambda: user.save())()

    await sync_to_async(terminate_all_user_sessions)(user)

    await event.ctx_api.messages.edit(
        peer_id=event.object.peer_id,
        cmid=event.object.conversation_message_id,
        message=
        f"Ваш пароль успешно сброшен!\n\n"
        f"Новый пароль: {password}\n\n"
        f"Запишите пароль и нажмите кнопку \"Скрыть\", чтобы скрыть его из сообщения\n"
        f"Придумать собственный пароль вы можете на сайте викторины, указанном в описании сообщества",
        keyboard=Keyboard(inline=True).add(Callback("Скрыть", {"action": "hide_password"})).get_json()
    )
