import uuid

from vkbottle import GroupTypes


async def stop_load_callback(event: GroupTypes.MessageEvent):
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        peer_id=event.object.peer_id,
        user_id=event.object.user_id,
    )


def generate_event_random_id():
    return int(uuid.uuid4().hex[:12], 16)
