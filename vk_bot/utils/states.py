from enum import Enum

import redis.asyncio as aioredis

from vk_bot.config_data.config import load_config

config = load_config()
redis_client = aioredis.from_url(config.redis.url, decode_responses=True)


class UserState(str, Enum):
    WAITING_FOR_CODE = "waiting_for_code"


async def set_state(user_id: int, state: UserState, ttl_seconds: int = 600) -> None:
    """
    Устанавливает состояние пользователя с тайм-аутом (по умолчанию 10 минут).
    """
    await redis_client.set(name=f"vk_bot:state:{user_id}", value=state.value, ex=ttl_seconds)


async def get_state(user_id: int) -> str | None:
    """
    Получает текущее состояние пользователя.
    """
    return await redis_client.get(name=f"vk_bot:state:{user_id}")


async def clear_state(user_id: int) -> None:
    """
    Сбрасывает состояние пользователя.
    """
    await redis_client.delete(f"vk_bot:state:{user_id}")
