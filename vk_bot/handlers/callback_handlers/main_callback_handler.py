import random
import string

from vkbottle import Callback
from vkbottle import GroupTypes
from vkbottle.tools import Keyboard

from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.utils.db import create_user_and_profile
from vk_bot.utils.db import get_current_user


async def go_main(event: GroupTypes.MessageEvent):
    kb = create_main_menu_keyboard()

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=0,
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )


async def check_profile(event: GroupTypes.MessageEvent):
    user_profile, user = await get_current_user(event.object.user_id)
    if user is None:
        kb = (
            Keyboard()
            .add(Callback("Создать профиль", {"action": "create_profile"}))
            .row()
            .add(Callback("Назад", {"action": "go_main"}))
        ).get_json()

        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            random_id=0,
            message="У вас нет аккаунта!",
            keyboard=kb
        )
    else:

        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            random_id=0,
            message=
            "Ваш профиль:\n\n"
            f"Логин: {user.username}\n"
        )


async def create_profile(event: GroupTypes.MessageEvent):
    username = f"vk_{event.object.user_id}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    await create_user_and_profile(username, password, event.object.user_id)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=0,
        message=
        f"Ваш аккаунт успешно создан!\n\n"
        f"Логин: {username}\n"
        f"Пароль: {password}\n\n"
        f"Запишите пароль и нажмите кнопку \"Скрыть\", чтобы скрыть его из сообщения",
        keyboard=Keyboard(inline=True).add(Callback("Скрыть", {"action": "hide_password"})).get_json()
    )

    kb = create_main_menu_keyboard()

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=0,
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )

async def hide_password(event: GroupTypes.MessageEvent):
    await event.ctx_api.messages.edit(
        peer_id=event.object.peer_id,
        cmid=event.object.conversation_message_id,
        message="Ваш аккаунт успешно создан!",
    )