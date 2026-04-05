from dataclasses import dataclass

from environs import Env


@dataclass
class VkBot:
    token: str


@dataclass
class DataBase:
    pass


@dataclass
class VkBotConfig:
    vkBot: VkBot


def load_config(path: str | None = None) -> VkBotConfig:
    env = Env()
    env.read_env()
    config: VkBotConfig = VkBotConfig(
        vkBot=VkBot(token=env("VK_BOT_TOKEN"))
    )

    return config
