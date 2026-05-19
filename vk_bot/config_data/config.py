from dataclasses import dataclass

from environs import Env


@dataclass
class VkBot:
    token: str


@dataclass
class RedisConfig:
    url: str


@dataclass
class DataBase:
    pass


@dataclass
class VkBotConfig:
    vkBot: VkBot
    redis: RedisConfig


def load_config(path: str | None = None) -> VkBotConfig:
    env = Env()
    env.read_env()
    config = VkBotConfig(
        vkBot=VkBot(token=env("VK_BOT_TOKEN")),
        redis=RedisConfig(url=env.str("REDIS_URL", "redis://localhost:6379/0")),
    )

    return config
