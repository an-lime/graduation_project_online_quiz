from vkbottle import GroupEventType, GroupTypes
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler

from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.utils.support_functions import stop_load_callback
from .callback_handlers.main_callback_handler import check_profile, create_profile, go_main, hide_password

main_labeler = BotLabeler()


@main_labeler.message(text="Начать")
async def start_command(message: Message):
    kb = create_main_menu_keyboard()

    await message.answer(
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )


@main_labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def callback_catch(event: GroupTypes.MessageEvent):
    await stop_load_callback(event)

    match event.object.payload.get("action"):
        case "go_main":
            await go_main(event)
        case "check_profile":
            await check_profile(event)
        case "create_profile":
            await create_profile(event)
        case "hide_password":
            await hide_password(event)
