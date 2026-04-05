import asyncio
import logging

from vkbottle import Bot
from vkbottle.framework.labeler import BotLabeler

from config_data.config import VkBotConfig, load_config
from handlers import main_labeler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Bot started...")

    config: VkBotConfig = load_config()

    bot = Bot(token=config.vkBot.token)
    bot.labeler.load(main_labeler)

    bot.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
