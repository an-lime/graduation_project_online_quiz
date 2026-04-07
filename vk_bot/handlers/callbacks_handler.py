from vkbottle import GroupEventType, GroupTypes
from vkbottle.framework.labeler import BotLabeler

callback_labeler = BotLabeler()


@callback_labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def handle_message_event(event: GroupTypes.MessageEvent):
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        peer_id=event.object.peer_id,
        user_id=event.object.user_id,
    )

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        random_id=0,
        message="miau miau",
    )
