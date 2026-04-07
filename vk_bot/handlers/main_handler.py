from vkbottle import Text, Callback
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler
from vkbottle.tools import Keyboard

from vk_bot.utils.db import get_current_user

main_labeler = BotLabeler()


@main_labeler.message(text="Начать")
async def start_command(message: Message):
    kb = (
        Keyboard(one_time=False)
        .add(Text("Проверить профиль"))
    ).get_json()

    await message.answer(
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )


@main_labeler.message(text="Проверить профиль")
async def check_profile(message: Message):
    user = await get_current_user(message.from_id)
    if user is None:
        kb = (
            Keyboard(one_time=False)
            .add(Callback("Создать профиль", {"action": "create_profile"}))
        ).get_json()

        await message.answer(
            "У вас нет аккаунта!",
            keyboard=kb
        )
