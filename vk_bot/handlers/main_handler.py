import json
import logging

from vkbottle import GroupEventType, GroupTypes
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler

from vk_bot.keyboards.main_keyboard import create_main_menu_keyboard
from vk_bot.utils.states import get_state, UserState
from .callback_handlers.game_callback_handler import process_game_code, join_game, cancel_join, leave_lobby, \
    handle_answer_callback, confirm_leave_lobby, cancel_leave_lobby
from .callback_handlers.main_callback_handler import my_profile, create_profile, go_main, hide_password, reset_password, \
    confirm_reset

logger = logging.getLogger(__name__)

main_labeler = BotLabeler()


@main_labeler.message(text=["Начать", "начать"])
async def start_command(message: Message):
    kb = create_main_menu_keyboard()

    await message.answer(
        message="Приветствую тебя в боте для викторин!",
        keyboard=kb
    )


@main_labeler.message()
async def catch_any_message(message: Message):
    current_state = await get_state(message.from_id)

    if current_state == UserState.WAITING_FOR_CODE.value:
        await process_game_code(message)
        return

    kb = create_main_menu_keyboard()
    await message.answer(
        "Я не понимаю эту команду 😔\nПожалуйста, воспользуйтесь кнопками меню.",
        keyboard=kb
    )


@main_labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def callback_catch(event: GroupTypes.MessageEvent):
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        peer_id=event.object.peer_id,
        user_id=event.object.user_id,
    )

    raw_payload = event.object.payload
    if isinstance(raw_payload, str):
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = raw_payload or {}

    action = payload.get("action")
    logger.info(f"📥 Callback received: action={action}, payload={payload}")

    match action:
        case "go_main":
            await go_main(event)
        case "my_profile":
            await my_profile(event)
        case "create_profile":
            await create_profile(event)
        case "hide_password":
            await hide_password(event)
        case "reset_password":
            await reset_password(event)
        case "confirm_reset":
            await confirm_reset(event)
        case "join_game":
            await join_game(event)
        case "cancel_join":
            await cancel_join(event)
        case "leave_lobby":
            await leave_lobby(event, payload)
        case "confirm_leave_lobby":
            await confirm_leave_lobby(event, payload)
        case "cancel_leave_lobby":
            await cancel_leave_lobby(event, payload)
        case "answer":
            await handle_answer_callback(event, payload)
